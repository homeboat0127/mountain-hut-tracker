/**
 * 台灣百岳資訊站 — 網友回饋收集與每日通知
 *
 * 這份程式碼要貼到 Google Apps Script（script.google.com）執行，不是網站的程式。
 *
 * 功能：
 *   1. 接收網站回饋表單送出的資料，寫進 Google 試算表
 *   2. 每天 20:00 檢查，「當天有新回饋才寄信」到指定信箱，沒有就不寄
 *
 * 使用步驟：
 *   1. 到 https://script.google.com 建立新專案，把這整份貼上取代原有內容
 *   2. 上方函式選單選「setup」，按執行（會要求授權，允許即可）
 *      → 這一步會自動建立試算表、設定每天 20:00 的排程
 *   3. 右上「部署」→「新增部署作業」→ 類型選「網頁應用程式」
 *      執行身分：我自己
 *      具有存取權的使用者：「所有人」（重要，否則網站送不進來）
 *   4. 部署後複製「網頁應用程式網址」，回報給開發者接上網站
 */

// 收到回饋要通知的信箱
const NOTIFY_EMAIL = 'homeboat0127@gmail.com';

// 試算表名稱
const SHEET_NAME = '台灣百岳資訊站 - 網友回饋';

// 每天寄送摘要的時間（24 小時制）
const DIGEST_HOUR = 20;


/**
 * 只需執行一次：建立試算表、寫入標題列、設定每日排程。
 * 重複執行不會重建試算表，也不會產生重複排程。
 */
function setup() {
  const ss = getOrCreateSpreadsheet_();
  const sheet = ss.getSheets()[0];

  // 標題列（只在空白時寫入，避免蓋掉既有資料）
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['送出時間', '回饋類型', '相關山屋／路線', '回饋內容', '聯絡 Email', '處理狀態', '來源頁面']);
    sheet.getRange(1, 1, 1, 7).setFontWeight('bold').setBackground('#e6f3ea');
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(1, 150);
    sheet.setColumnWidth(2, 130);
    sheet.setColumnWidth(3, 150);
    sheet.setColumnWidth(4, 420);
    sheet.setColumnWidth(5, 200);
    sheet.setColumnWidth(6, 100);
  }

  // 清掉舊排程再重設，避免重複執行導致一天寄好幾封
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'sendDailyDigest') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('sendDailyDigest').timeBased().atHour(DIGEST_HOUR).everyDays(1).create();

  Logger.log('設定完成');
  Logger.log('試算表網址：' + ss.getUrl());
  Logger.log('每日 ' + DIGEST_HOUR + ':00 會檢查是否有新回饋');
  return ss.getUrl();
}


/**
 * 網站表單送出時會呼叫這裡。
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    // 防機器人：honeypot 是隱藏欄位，正常使用者看不到也不會填，有值就是機器人
    if (data.website) {
      return jsonResponse_({ ok: true });   // 假裝成功，不讓機器人知道被擋
    }

    const message = String(data.message || '').trim();
    if (!message || message.length < 5) {
      return jsonResponse_({ ok: false, error: '回饋內容太短' });
    }

    // 多人同時送出時，若不上鎖，兩筆資料可能搶同一列而導致其中一筆遺失。
    // 這裡最多等 10 秒取得鎖，確保每筆回饋都完整寫入。
    const lock = LockService.getScriptLock();
    if (!lock.tryLock(10000)) {
      return jsonResponse_({ ok: false, error: '系統忙碌中，請稍後再送出一次' });
    }

    try {
      const sheet = getOrCreateSpreadsheet_().getSheets()[0];
      sheet.appendRow([
        new Date(),
        String(data.type || '未分類').slice(0, 50),
        String(data.target || '').slice(0, 100),
        message.slice(0, 3000),
        String(data.email || '').slice(0, 150),
        '未處理',
        String(data.page || '').slice(0, 300),
      ]);
    } finally {
      lock.releaseLock();
    }

    return jsonResponse_({ ok: true });
  } catch (err) {
    return jsonResponse_({ ok: false, error: String(err) });
  }
}


/**
 * 每天 20:00 自動執行：只有當天有新回饋才寄信。
 */
function sendDailyDigest() {
  const sheet = getOrCreateSpreadsheet_().getSheets()[0];
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return;   // 只有標題列，沒資料

  const rows = sheet.getRange(2, 1, lastRow - 1, 7).getValues();

  // 取「過去 24 小時內」送出的回饋
  const since = new Date();
  since.setHours(since.getHours() - 24);
  const fresh = rows.filter(function (r) {
    return r[0] instanceof Date && r[0] >= since;
  });

  if (fresh.length === 0) {
    Logger.log('今日無新回饋，不寄信');
    return;
  }

  // 萬一某天湧入大量回饋，信件全列出去會過長也可能超出執行時間，
  // 這裡最多列出 50 則，其餘請直接開試算表看。
  const MAX_IN_MAIL = 50;
  const shown = fresh.slice(0, MAX_IN_MAIL);
  const rest = fresh.length - shown.length;

  const tz = Session.getScriptTimeZone();
  let html = '<div style="font-family:-apple-system,\'PingFang TC\',sans-serif;color:#223324;">';
  html += '<h2 style="color:#1f5c3b;">台灣百岳資訊站　今日新回饋 ' + fresh.length + ' 則</h2>';

  shown.forEach(function (r, i) {
    const when = Utilities.formatDate(r[0], tz, 'MM/dd HH:mm');
    html += '<div style="border:1px solid #e4e4e4;border-left:4px solid #2f7d52;border-radius:8px;padding:12px 14px;margin-bottom:12px;">';
    html += '<div style="font-size:12px;color:#888;">' + when + '　｜　' + escapeHtml_(r[1]) + '</div>';
    if (r[2]) html += '<div style="font-size:13px;font-weight:700;margin-top:4px;">相關：' + escapeHtml_(r[2]) + '</div>';
    html += '<div style="margin-top:8px;line-height:1.7;white-space:pre-wrap;">' + escapeHtml_(r[3]) + '</div>';
    if (r[4]) html += '<div style="font-size:12px;color:#2f7d52;margin-top:8px;">回覆信箱：' + escapeHtml_(r[4]) + '</div>';
    html += '</div>';
  });

  if (rest > 0) {
    html += '<p style="font-size:13px;color:#b9770e;">另有 ' + rest + ' 則未列出，請直接開啟試算表查看。</p>';
  }
  html += '<p style="font-size:12px;color:#888;">完整紀錄：<a href="' + getOrCreateSpreadsheet_().getUrl() + '">開啟試算表</a></p>';
  html += '</div>';

  MailApp.sendEmail({
    to: NOTIFY_EMAIL,
    subject: '【台灣百岳資訊站】今日新回饋 ' + fresh.length + ' 則',
    htmlBody: html,
  });
  Logger.log('已寄出 ' + fresh.length + ' 則回饋');
}


/* ---------- 內部工具 ---------- */

function getOrCreateSpreadsheet_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty('SHEET_ID');
  if (id) {
    try { return SpreadsheetApp.openById(id); } catch (e) { /* 找不到就重建 */ }
  }
  const ss = SpreadsheetApp.create(SHEET_NAME);
  props.setProperty('SHEET_ID', ss.getId());
  return ss;
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function escapeHtml_(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
