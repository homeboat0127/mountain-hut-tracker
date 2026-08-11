import json
import os
import re
import sys
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

URL = "https://hike.taiwan.gov.tw/bed_6.aspx"
MOUNTAIN = "玉山"

HUTS = [
    {"value": "3", "name": "排雲山莊"},
    {"value": "4", "name": "圓峰山屋/營地"},
    {"value": "221", "name": "荖濃溪營地"},
    {"value": "222", "name": "樂樂山屋"},
    {"value": "727", "name": "觀高山屋"},
    {"value": "223", "name": "巴奈伊克營地"},
    {"value": "224", "name": "中央金礦山屋"},
    {"value": "225", "name": "白洋金礦山屋/營地"},
    {"value": "226", "name": "杜鵑營地"},
    {"value": "227", "name": "南營地"},
    {"value": "228", "name": "大水窟山屋"},
    {"value": "229", "name": "塔芬谷山屋"},
    {"value": "230", "name": "轆轆谷山屋"},
    {"value": "231", "name": "雲峰下三叉營地"},
    {"value": "232", "name": "拉庫音溪山屋"},
    {"value": "233", "name": "馬博山屋"},
    {"value": "234", "name": "馬利加南山屋"},
    {"value": "235", "name": "馬布谷山屋"},
    {"value": "6", "name": "佳心營地"},
    {"value": "7", "name": "瓦拉米山屋/營地"},
    {"value": "215", "name": "抱崖山屋/營地"},
    {"value": "236", "name": "多美麗營地"},
    {"value": "237", "name": "大分山屋"},
    {"value": "238", "name": "托馬斯營地"},
    {"value": "239", "name": "庫哈諾辛山屋/營地"},
    {"value": "240", "name": "連理山前(桃源)營地"},
    {"value": "241", "name": "新仙山前營地"},
]

FOREST_URL = "https://hike.taiwan.gov.tw/bed_0.aspx"

FOREST_HUTS = [
    {"value": "B80BDDE7-8F9D-4008-9FA8-81B0D5F4492F", "name": "天池山莊/營地"},
    {"value": "C578142E-AE41-41B2-8169-39D8A8462F37", "name": "向陽山屋"},
    {"value": "60D5A789-676C-47D6-8F6D-2B991A5D730D", "name": "嘉明湖山屋/營地"},
    {"value": "A589B1FE-0296-478E-ADB5-99ACCF2DCC25", "name": "檜谷山莊/營地"},
]

TAROKO_URL = "https://hike.taiwan.gov.tw/bed_4.aspx"

TAROKO_HUTS = [
    {"value": "124", "name": "黑水塘山屋"},
    {"value": "125", "name": "成功山屋"},
    {"value": "126", "name": "成功二號堡"},
    {"value": "127", "name": "奇萊山屋"},
    {"value": "149", "name": "雲稜山屋"},
    {"value": "151", "name": "審馬陣山屋"},
    {"value": "152", "name": "南湖山屋"},
    {"value": "626", "name": "鋸東避難小屋"},
    {"value": "627", "name": "屏風避難山屋"},
    {"value": "666", "name": "雲稜營地"},
    {"value": "667", "name": "南湖營地"},
    {"value": "691", "name": "磐石中峰避難小屋"},
    {"value": "692", "name": "三叉營地避難小屋"},
    {"value": "693", "name": "大理石營地避難小屋"},
]

SNOW_URL = "https://hike.taiwan.gov.tw/bed_1.aspx"

SNOW_HUTS = [
    {"value": "675", "name": "三六九臨時營地"},
    {"value": "10", "name": "七卡山莊"},
    {"value": "386", "name": "七卡營地"},
    {"value": "13", "name": "三六九山莊"},
    {"value": "17", "name": "翠池山屋"},
    {"value": "387", "name": "翠池營地"},
    {"value": "58", "name": "桃山山莊"},
    {"value": "409", "name": "桃山營地"},
    {"value": "63", "name": "新達山屋"},
    {"value": "411", "name": "新達營地"},
    {"value": "412", "name": "馬達拉溪登山口宿營地"},
    {"value": "68", "name": "九九山莊"},
    {"value": "304", "name": "中霸山屋"},
    {"value": "389", "name": "賽良久營地"},
    {"value": "671", "name": "瓢簞山屋"},
    {"value": "672", "name": "瓢簞營地"},
    {"value": "391", "name": "雪山山莊舊址營地"},
    {"value": "670", "name": "油婆蘭山屋"},
    {"value": "673", "name": "油婆蘭營地"},
    {"value": "393", "name": "完美谷營地"},
    {"value": "394", "name": "17K營地"},
    {"value": "395", "name": "26K營地"},
    {"value": "396", "name": "28K營地"},
    {"value": "400", "name": "匹匹達山東鞍營地"},
    {"value": "401", "name": "奇峻山營地"},
    {"value": "397", "name": "弓水營地"},
    {"value": "398", "name": "大南山西鞍營地"},
    {"value": "399", "name": "火石山下營地"},
    {"value": "85", "name": "雪北山屋"},
    {"value": "83", "name": "素密達山屋"},
    {"value": "79", "name": "霸南山屋"},
    {"value": "413", "name": "馬洋山前營地"},
    {"value": "414", "name": "馬洋池營地"},
    {"value": "382", "name": "雪山圈谷營地"},
]

TW = timezone(timedelta(hours=8))


def parse_day_cell(cell):
    link = cell.query_selector("a")
    if not link:
        return None

    href = link.get_attribute("href") or ""
    m = re.search(r"sdate=(\d{4}-\d{2}-\d{2})", href)
    date = m.group(1) if m else None

    # 山屋因活動/工程等原因整日關閉，該格只會出現「相關訊息」連結，而非額滿/餘額資訊
    if link.get_attribute("id") == "stopdate":
        return {
            "date": date,
            "status": "關閉",
            "bed_avail": 0,
            "tent_avail": 0,
            "queue": None,
            "reviewing": None,
            "approved": None,
            "total_bed_used": None,
            "total_tent_used": None,
            "note": None,
            "_closure_href": href,
        }

    text = link.inner_text()

    status = "額滿" if "額滿" in text else ("餘額" if "餘額" in text else None)

    bed_avail = tent_avail = 0
    nums = re.findall(r"\((\d+),(\d+)\)", text)
    if status == "餘額" and nums:
        bed_avail, tent_avail = int(nums[0][0]), int(nums[0][1])

    def grab(label):
        mm = re.search(label + r"\s*(\d+)", text)
        return int(mm.group(1)) if mm else None

    queue = grab("排隊預約")
    reviewing = grab("審核中")
    approved = grab("核准入園")

    total_bed_used = total_tent_used = None
    if nums:
        total_bed_used, total_tent_used = int(nums[-1][0]), int(nums[-1][1])

    return {
        "date": date,
        "status": status,
        "bed_avail": bed_avail,
        "tent_avail": tent_avail,
        "queue": queue,
        "reviewing": reviewing,
        "approved": approved,
        "total_bed_used": total_bed_used,
        "total_tent_used": total_tent_used,
        "note": None,
    }


def fetch_closure_reason(page, href):
    """抓「關閉原因」說明頁。這是附加資訊，抓不到不影響主要資料，
    因此逾時或任何錯誤都只回 None，不讓整批排程因為一頁失敗而中斷。"""
    full_url = "https://hike.taiwan.gov.tw/" + href
    try:
        page.goto(full_url, wait_until="domcontentloaded", timeout=15000)
        text = page.inner_text("body")
    except Exception as e:
        print(f"  [警告] 取得關閉原因失敗，略過：{href} ({type(e).__name__})")
        return None

    lines = [l for l in text.split("\n") if l.strip()]
    for line in lines:
        cols = line.split("\t")
        if len(cols) >= 3 and cols[0].strip() != "節點名稱":
            return cols[2].strip()
    return None


def _grab_int(text, label):
    m = re.search(label + r"\D*(\d+)", text)
    return int(m.group(1)) if m else None


def scrape_hut(page, detail_page, hut_value, hut_name):
    page.select_option("#con_rooms", hut_value)
    page.wait_for_timeout(300)

    with page.expect_response(lambda r: "bed_6.aspx" in r.url, timeout=20000):
        page.click("#con_btnsearch")

    for _ in range(20):
        if page.query_selector("table.table_bed td a"):
            break
        page.wait_for_timeout(500)
    page.wait_for_timeout(500)

    overview_text = page.inner_text("body")
    cap_weekday_bed = _grab_int(overview_text, "非假日床位")
    cap_weekend_bed = _grab_int(overview_text, "假日床位")
    cap_weekday_tent = _grab_int(overview_text, "非假日營帳")
    cap_weekend_tent = _grab_int(overview_text, "假日營帳")

    cells = page.query_selector_all("table.table_bed tbody td")
    days = []
    for cell in cells:
        d = parse_day_cell(cell)
        if d and d["date"]:
            days.append(d)

    # 關閉日的說明在另一個頁面，用獨立分頁抓取，避免打斷主查詢頁面狀態
    for d in days:
        href = d.pop("_closure_href", None)
        if href:
            d["note"] = fetch_closure_reason(detail_page, href)

    # 依承載量判斷是山屋（有床位）、營地（有營位），或兩者皆有，讓前端可以分開顯示
    has_bed = bool(cap_weekday_bed) or bool(cap_weekend_bed)
    has_tent = bool(cap_weekday_tent) or bool(cap_weekend_tent)
    if has_bed and has_tent:
        node_type = "山屋＋營地"
    elif has_bed:
        node_type = "山屋"
    elif has_tent:
        node_type = "營地"
    else:
        node_type = "未知"

    return {
        "name": hut_name,
        "mountain": MOUNTAIN,
        "type": node_type,
        "capacity_weekday_bed": cap_weekday_bed,
        "capacity_weekend_bed": cap_weekend_bed,
        "capacity_weekday_tent": cap_weekday_tent,
        "capacity_weekend_tent": cap_weekend_tent,
        "days": days,
    }


def parse_forest_day_cell(cell, year, month):
    p_tag = cell.query_selector("p")
    day_text = p_tag.inner_text().strip() if p_tag else ""
    if not day_text.isdigit():
        return None

    cc = cell.query_selector("span[id^='con_cc_']")
    text = cc.inner_text() if cc else ""
    if not text.strip():
        return None

    items = re.findall(r"([^\n]+?)\n剩餘數量\s*(\d+)\s*\n現在申請數\s*(\d+)", text)
    if not items:
        return None

    day = int(day_text)
    return {
        "date": f"{year}-{month:02d}-{day:02d}",
        "items": [
            {"label": label.strip(), "remaining": int(remaining), "applications": int(applications)}
            for label, remaining, applications in items
        ],
    }


def scrape_forest_hut(page, hut_value, hut_name, year, month):
    page.select_option("#con_rooms", hut_value)
    page.wait_for_timeout(300)

    with page.expect_response(lambda r: "bed_0.aspx" in r.url, timeout=20000):
        page.click("#con_btnsearch")

    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    for _ in range(20):
        try:
            if page.query_selector("table.table_bed td span[id^='con_cc_']"):
                break
        except Exception:
            pass
        page.wait_for_timeout(500)
    page.wait_for_timeout(500)

    cells = page.query_selector_all("table.table_bed tbody td")
    days = []
    for cell in cells:
        d = parse_forest_day_cell(cell, year, month)
        if d:
            days.append(d)

    return {
        "name": hut_name,
        "days": days,
    }


def parse_progress_day_cell(cell, year, month):
    cb = cell.query_selector("span[id^='con_cb_']")
    if not cb:
        return None
    day_text = cb.inner_text().strip()
    if not day_text.isdigit():
        return None
    day = int(day_text)
    date = f"{year}-{month:02d}-{day:02d}"

    cc = cell.query_selector("span[id^='con_cc_']")
    cc_text = cc.inner_text().strip() if cc else ""

    # 山屋長期停止申請（例如整修）時，該格沒有連結，直接顯示「本日關閉」文字
    if "關閉" in cc_text:
        return {"date": date, "fields": {}, "closed": True, "note": cc_text}

    link = cell.query_selector("span[id^='con_cc_'] a")
    if not link:
        return None

    text = link.inner_text()
    if not text.strip():
        return None

    # 太魯閣／雪霸系統格式：每行「標籤 數字」，例如「餘額 6」「待處理 0」「已通過 0」
    pairs = re.findall(r"([^\n\xa0]+)\xa0+(\d+)", text)
    if not pairs:
        return None

    fields = {label.strip(): int(value) for label, value in pairs}

    return {
        "date": date,
        "fields": fields,
        "closed": False,
        "note": None,
    }


def scrape_progress_hut(page, base_url, hut_value, hut_name, year, month):
    page.select_option("#con_rooms", hut_value)
    page.wait_for_timeout(300)

    with page.expect_response(lambda r: base_url.split("/")[-1] in r.url, timeout=20000):
        page.click("#con_btnsearch")

    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    for _ in range(20):
        try:
            cc = page.query_selector("table.table_bed td span[id^='con_cc_']")
            if cc and cc.inner_text().strip():
                break
        except Exception:
            pass
        page.wait_for_timeout(500)
    page.wait_for_timeout(500)

    cells = page.query_selector_all("table.table_bed tbody td")
    days = []
    for cell in cells:
        d = parse_progress_day_cell(cell, year, month)
        if d:
            days.append(d)

    return {
        "name": hut_name,
        "days": days,
    }


def next_month_year(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)



def safe_scrape(label, fn, fallback):
    """單一山屋抓取失敗時只記錄警告並回傳空資料，避免整批排程中斷。"""
    try:
        return fn()
    except Exception as e:
        print(f"  [警告] {label} 抓取失敗，略過：{type(e).__name__}: {e}")
        return fallback


# ---------------------------------------------------------------------------
# 公告類資料：封園（可退費期間）與抽籤時間
#
# 兩個來源都只涵蓋玉山國家公園系統，雪霸／太魯閣／林業保育署沒有對應的期間型
# 公告頁面。前端必須把這個範圍限制講明白，否則使用者會把「沒有警示」誤讀成
# 「已確認安全」。
# ---------------------------------------------------------------------------

CLOSURE_URL = "https://hike.taiwan.gov.tw/bed_9.aspx"   # 玉山可申請退費日期查詢
LOTTERY_URL = "https://hike.taiwan.gov.tw/bed_8.aspx"   # 玉山抽籤日期

# 民國年日期，例如「115年7月14日」「115-7-14」
ROC_DATE = r'(\d{2,3})\s*[-年]\s*(\d{1,2})\s*[-月]\s*(\d{1,2})'


def _roc_to_iso(m):
    return f"{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def _grid_rows(page, table_id="con_gvData", max_pages=12):
    """讀完 ASP.NET GridView 的所有分頁。

    先把頁碼全部讀出來再逐一點過去，不靠「下一頁」推進 —— 用下一頁判斷終點時，
    只要頁面結構稍有不同就會判斷不出終點而無限空轉（開發時實際踩到）。
    """
    nums = page.eval_on_selector_all(
        f"#{table_id} a", "els => els.map(a => a.innerText.trim()).filter(t => /^\\d+$/.test(t))")
    pages = sorted({int(n) for n in nums} | {1})[:max_pages]
    rows, seen = [], set()

    def collect():
        for r in page.eval_on_selector_all(
                f"#{table_id} tr",
                "els => els.map(tr => Array.from(tr.cells).map(td => td.innerText.trim()))"):
            if len(r) < 2 or not r[0]:
                continue
            key = "|".join(r)
            if key not in seen:
                seen.add(key)
                rows.append(r)

    collect()
    for n in pages:
        if n == 1:
            continue
        link = page.query_selector(f"#{table_id} a:text-is('{n}')")
        if link:
            link.click()
            page.wait_for_timeout(1000)
            collect()
    return rows


def scrape_closures(page):
    """爬「玉山可申請退費日期查詢」，判定哪些期間屬於真正的封園。

    這裡最容易出錯的一點：這張表的欄位是「未入園可退費期間」，不是封園期間。
    兩者不相等，實測 17 筆裡只有 1 筆是全期間禁止入園：

      - 6 成以上是豪雨特報造成的可退費期間，內文根本沒有「禁止入園」字樣
      - 有幾筆雖然禁止入園，但內文另外公告了恢復日，且恢復日早於期間結束日
        （例如排雲山莊 7/07~7/19，公告 7/14 起恢復，7/14~7/19 其實是開放的）

    若把可退費期間直接當封園期間，會把開放日標成封園，使用者可能因此放棄一趟
    本來可以成行的行程 —— 這同時違反資料授權「不得展示與原資料不符之資訊」。

    因此只有「明確禁止入園」且「沒有公告恢復日」才標記為 confirmed，
    由前端灰化該期間名額；其餘一律只顯示原文提示，不動名額數字。
    """
    page.goto(CLOSURE_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1200)

    closures = []
    for r in _grid_rows(page):
        if len(r) < 5 or "退費期間" in r[0]:
            continue
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', r[0].replace("\n", ""))
        if len(dates) < 2:
            continue
        message = " ".join(r[4].split())
        prohibits = bool(re.search(r'禁止.{0,8}入園', message))
        rec = re.search(r'自\s*' + ROC_DATE + r'\s*日?\s*起.{0,6}恢復', message)
        recovery = _roc_to_iso(rec) if rec else None
        closures.append({
            "start": dates[0],
            "end": dates[1],
            "sites": [s.strip() for s in re.split(r'[、,]', r[1]) if s.strip()],
            "reason_type": r[2],
            "reason": r[3],
            "message": message,
            "prohibits_entry": prohibits,
            "recovery_date": recovery,
            # confirmed=True 才會讓前端灰化名額。寧可少灰化，不要灰化錯。
            "confirmed": bool(prohibits and not recovery),
        })
    closures.sort(key=lambda c: c["start"], reverse=True)
    print(f"  封園公告：{len(closures)} 筆，其中確認全期間禁止入園 "
          f"{sum(1 for c in closures if c['confirmed'])} 筆")
    return closures


# 登山路線開放狀態頁：四個機關通用，提供每條路線需要哪些證件。
# 這是唯一一份能一次涵蓋四系統的官方結構化資料，用來補「入園證／入山證的
# 適用差異」—— 兩者主管機關不同（國家公園署／警政署），新手常以為申請了
# 入園證就好。實測差異是實質的：玉山與南湖要兩證，雪山與奇萊只要入園證，
# 嘉明湖不在國家公園內，是住宿申請加入山證。
PERMIT_URL = "https://hike.taiwan.gov.tw/open.aspx"

# 官方路線名稱清單。必須與 huts.html 各走法的 officialRoute 完全一致，
# 對不上就查不到證件資料（前端會顯示「尚未查證」而非猜測）。
PERMIT_ROUTES = [
    "2~5天(塔塔加 - 玉山線 - 塔塔加)",
    "玉山線單日往返",
    "(3級) 雪山主峰(多日行程)",
    "(4級) 雪山主峰(單日往返)",
    "奇萊主、北峰線",
    "南湖大山線(因承載量異動，入園日期為114.7.1以後者適用)",
    "嘉明湖山屋/營地",
    "向陽山屋",
]

PERMIT_COLS = ["機關", "登山主路線", "路線名稱", "可否申請", "路線現況",
               "入園證", "自然保護留區", "住宿", "入山證", "難度等級"]


def scrape_permits(page):
    """逐條查詢路線所需證件。

    只查我們實際收錄的 8 條官方路線，不掃全部 437 條 —— 沒用到的資料不抓，
    對政府網站的負擔也小。原生 select 被自訂下拉蓋住，因此用 JS 設值後
    再觸發查詢按鈕。
    """
    page.goto(PERMIT_URL, wait_until="networkidle", timeout=60000)
    # 前一次抓取可能讓頁面停在別的狀態，等下拉真的出現再繼續，
    # 否則會拿到 null 而整批失敗（實際發生過）。
    page.wait_for_selector("#con_line", timeout=20000)
    page.wait_for_timeout(800)

    permits = {}
    for name in PERMIT_ROUTES:
        found = page.evaluate("""(name) => {
            const s = document.getElementById('con_line');
            const o = Array.from(s.options).find(x => x.text.trim() === name);
            if (!o) return false;
            s.value = o.value;
            s.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
        }""", name)
        if not found:
            print(f"  [警告] 找不到官方路線選項：{name}")
            continue
        page.wait_for_timeout(250)
        page.evaluate("""() => {
            const a = Array.from(document.querySelectorAll('a,button,input[type=button],input[type=submit]'))
              .find(e => (e.innerText || e.value || '').trim() === '查詢' && e.id !== 'btngoogle');
            if (a) a.click();
        }""")
        page.wait_for_timeout(2200)

        rows = page.evaluate("""() => {
            const t = document.querySelector('table');
            if (!t) return [];
            return Array.from(t.rows).slice(2)
              .map(r => Array.from(r.cells).map(c => c.innerText.trim().replace(/\\s+/g, ' ')));
        }""")
        rows = [r for r in rows if len(r) >= 10 and r[2] == name]
        if not rows:
            print(f"  [警告] {name} 查無資料")
            continue
        d = dict(zip(PERMIT_COLS, rows[0]))
        permits[name] = {
            "agency": d["機關"],
            "needs": [k for k in ("入園證", "自然保護留區", "住宿", "入山證") if d.get(k)],
            "difficulty": d.get("難度等級") or None,
            "can_apply": d.get("可否申請") or None,
            "status": d.get("路線現況") or None,
        }
    print(f"  路線證件：{len(permits)} / {len(PERMIT_ROUTES)} 條查得")
    return permits


# 單日往返路線的逐日名額。
#
# 為什麼要抓：站上原本寫「單攻僅需申請入園證」，是錯的 ——
# 單日往返一樣有每日承載量上限（玉山線每日 60 人且列入抽籤，前峰 100 人不抽籤），
# 寫成「僅需申請」會讓使用者以為隨到隨辦。
#
# 逐日資料的結構與玉山山屋月曆相同（餘額／排隊預約／審核中／核准入園），
# 差別在名額是單一數字而非「床位,營位」兩個數字。
ROUTE_QUOTA_URL = "https://hike.taiwan.gov.tw/bed_7.aspx"


def _parse_quota_cell(text, year, month):
    """解析單日往返月曆的一格。格式範例：
         15
         餘額 1
         排隊預約 17
         審核中 0
         核准入園 97
    只有日期沒有其他內容的格子（已過去的日期）回傳 None。
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None
    m = re.match(r"^(\d{1,2})$", lines[0])
    if not m:
        return None
    day = int(m.group(1))
    rest = " ".join(lines[1:])
    if not rest:
        return None    # 過去的日期只有數字，沒有名額資料

    status = "額滿" if "額滿" in rest else ("餘額" if "餘額" in rest else None)
    if status is None:
        return None

    def grab(label):
        mm = re.search(label + r"\s*(\d+)", rest)
        return int(mm.group(1)) if mm else None

    avail = grab("餘額") if status == "餘額" else 0
    return {
        "date": f"{year:04d}-{month:02d}-{day:02d}",
        "status": status,
        "avail": avail if avail is not None else 0,
        "queue": grab("排隊預約"),
        "reviewing": grab("審核中"),
        "approved": grab("核准入園"),
    }


def _read_quota_calendar(page, year, month):
    cells = page.evaluate("""() => {
        const t = document.querySelector('table');
        if (!t) return [];
        const out = [];
        Array.from(t.rows).slice(1).forEach(r =>
          Array.from(r.cells).forEach(c => { const x = c.innerText.trim(); if (x) out.push(x); }));
        return out;
    }""")
    days = []
    for text in cells:
        d = _parse_quota_cell(text, year, month)
        if d:
            days.append(d)
    return days


def scrape_route_quota(page, year, month, next_year, next_month):
    """抓五條單日往返路線的承載量與逐日名額（本月與次月）。"""
    page.goto(ROUTE_QUOTA_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1200)

    # 承載量表：路線 / 平日 / 假日 / 備註
    table = page.evaluate("""() => {
        const t = document.querySelector('table');
        if (!t) return [];
        return Array.from(t.rows).slice(1)
          .map(r => Array.from(r.cells).map(c => c.innerText.trim().replace(/\\s+/g, ' ')))
          .filter(r => r.length >= 3);
    }""")
    caps = {}
    for r in table:
        name = r[0]
        try:
            caps[name] = {
                "capacity_weekday": int(re.sub(r"\D", "", r[1]) or 0),
                "capacity_weekend": int(re.sub(r"\D", "", r[2]) or 0),
                "note": (r[3] if len(r) > 3 else "").replace("...more", "").strip() or None,
            }
        except ValueError:
            continue

    options = page.evaluate("""() => Array.from(document.getElementById('con_rooms').options)
        .filter(o => o.value).map(o => ({name: o.text.trim(), value: o.value}))""")

    # 固定等待時間在這個頁面不可靠 —— 實測會出現「延遲一拍」：
    # 讀到的是上一次查詢的結果，導致次月天數全部變成本月的天數。
    # 改成等 postback 回應，再輪詢確認頁面狀態真的等於目標值才讀。
    def _wait_state(expect_room=None, expect_month=None, tries=25):
        for _ in range(tries):
            st = page.evaluate("""() => {
                const r = document.getElementById('con_rooms');
                const m = document.getElementById('con_ddlMonth');
                return {room: r ? r.value : null, month: m ? m.value : null};
            }""")
            ok_room = expect_room is None or str(st["room"]) == str(expect_room)
            ok_month = expect_month is None or str(st["month"]) == str(expect_month)
            if ok_room and ok_month:
                return True
            page.wait_for_timeout(400)
        print(f"  [警告] 頁面狀態未同步（路線={expect_room} 月={expect_month}）")
        return False

    def select_route(value):
        page.evaluate("""(v) => {
            const s = document.getElementById('con_rooms');
            s.value = v; s.dispatchEvent(new Event('change', { bubbles: true }));
        }""", value)
        page.wait_for_timeout(200)
        try:
            with page.expect_response(lambda r: "bed_7" in r.url, timeout=20000):
                page.evaluate("""() => {
                    const a = Array.from(document.querySelectorAll('a,input[type=button],input[type=submit]'))
                      .find(e => (e.innerText || e.value || '').trim() === '查詢' && e.id !== 'btngoogle');
                    if (a) a.click();
                }""")
        except Exception:
            pass
        _wait_state(expect_room=value)
        page.wait_for_timeout(500)

    def set_month(mm):
        try:
            with page.expect_response(lambda r: "bed_7" in r.url, timeout=20000):
                page.evaluate("""(mm) => {
                    const m = document.getElementById('con_ddlMonth');
                    if (m) { m.value = String(mm); m.dispatchEvent(new Event('change', { bubbles: true })); }
                }""", mm)
        except Exception:
            pass
        _wait_state(expect_month=mm)
        page.wait_for_timeout(500)

    # 兩段式：先把所有路線的本月跑完，再整批切到次月跑第二輪。
    # 原本每條路線來回切月份，postback 還沒完成就讀下一輪，
    # 結果次月讀到的其實是本月（次月天數全都變成 17 天，九月卻有 30 天）。
    cur, nxt = [], []
    for opt in options:
        name, value = opt["name"], opt["value"]
        select_route(value)
        base = dict(caps.get(name, {}), name=name, value=value, type="route_quota")
        cur.append(dict(base, days=_read_quota_calendar(page, year, month)))

    for opt in options:
        name, value = opt["name"], opt["value"]
        select_route(value)
        set_month(next_month)
        base = dict(caps.get(name, {}), name=name, value=value, type="route_quota")
        nxt.append(dict(base, days=_read_quota_calendar(page, next_year, next_month)))
        set_month(month)

    total = sum(len(r["days"]) for r in cur) + sum(len(r["days"]) for r in nxt)
    print(f"  單日往返路線：{len(cur)} 條，共 {total} 天")
    return cur, nxt


# 太魯閣與雪霸的路線／登山口人數限制。
#
# 與玉山的差別要講清楚，否則會把兩種不同性質的數字混為一談：
#   太魯閣 bed_5   ：以「路線」為單位，例如錐麓古道每日 96 人
#   雪霸   bed_10  ：以「登山口」為單位，例如雪山登山口每日 160 人 ——
#                    這個額度由該登山口進入的所有路線共用，不是單攻專屬
#
# 另一個實測結果：太魯閣多數單攻路線其實標示「無限制」
#（閂山單攻、羊頭山單攻、清水山、畢祿山），只有錐麓古道有上限。
# 對無限制的路線硬套一個名額日曆會是錯的，因此只對有數字上限的抓逐日資料。
TRAIL_QUOTA_SOURCES = [
    {"system": "taroko", "label": "太魯閣國家公園", "scope": "路線",
     "url": "https://hike.taiwan.gov.tw/bed_5.aspx"},
    {"system": "snow", "label": "雪霸國家公園", "scope": "登山口",
     "url": "https://hike.taiwan.gov.tw/bed_10.aspx"},
]


def _quota_number(text):
    """把承載量欄位轉成數字。「無限制」回傳 None，代表沒有人數上限。"""
    t = (text or "").strip()
    if not t or "無限制" in t or "不限" in t:
        return None
    m = re.search(r"\d+", t.replace(",", ""))
    return int(m.group(0)) if m else None


def scrape_trail_quota(page, year, month, next_year, next_month):
    """抓太魯閣／雪霸的路線與登山口人數限制，有數字上限者一併抓逐日名額。"""
    out = []
    for src in TRAIL_QUOTA_SOURCES:
        page.goto(src["url"], wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1200)

        table = page.evaluate("""() => {
            const t = document.querySelector('table');
            if (!t) return [];
            return Array.from(t.rows).slice(1)
              .map(r => Array.from(r.cells).map(c => c.innerText.trim().replace(/\\s+/g, ' ')))
              .filter(r => r.length >= 3 && r[0]);
        }""")
        options = page.evaluate("""() => Array.from(document.getElementById('con_rooms').options)
            .filter(o => o.value).map(o => ({name: o.text.trim(), value: o.value}))""")
        by_name = {o["name"]: o["value"] for o in options}

        entries = []
        for r in table:
            name = r[0]
            wk, we = _quota_number(r[1]), _quota_number(r[2])
            entries.append({
                "name": name,
                "system": src["system"],
                "systemLabel": src["label"],
                "scope": src["scope"],
                "value": by_name.get(name),
                "capacity_weekday": wk,
                "capacity_weekend": we,
                "unlimited": wk is None and we is None,
                "note": (r[3] if len(r) > 3 else "").strip() or None,
                "days": [],
                "days_next_month": [],
            })

        limited = [e for e in entries if not e["unlimited"] and e["value"]]
        for e in limited:
            cur = safe_scrape(
                f"{src['label']}／{e['name']}",
                lambda e=e: scrape_progress_hut(page, src["url"], e["value"], e["name"], year, month),
                {"name": e["name"], "days": []})
            e["days"] = cur.get("days", [])

        # 次月：整批切換月份後再跑一次，比每條路線來回切省時間
        try:
            page.evaluate("""(mm) => {
                const m = document.getElementById('con_ddlMonth');
                if (m) { m.value = String(mm); m.dispatchEvent(new Event('change', { bubbles: true })); }
            }""", next_month)
            page.wait_for_timeout(2000)
            for e in limited:
                nxt = safe_scrape(
                    f"{src['label']}／{e['name']}（下個月）",
                    lambda e=e: scrape_progress_hut(page, src["url"], e["value"], e["name"], next_year, next_month),
                    {"name": e["name"], "days": []})
                e["days_next_month"] = nxt.get("days", [])
        except Exception as ex:
            print(f"  [警告] {src['label']} 次月資料略過：{type(ex).__name__}")

        n_lim = len(limited)
        n_unlim = sum(1 for e in entries if e["unlimited"])
        total_days = sum(len(e["days"]) + len(e["days_next_month"]) for e in entries)
        print(f"  {src['label']}（依{src['scope']}）：{len(entries)} 項"
              f"（有上限 {n_lim}、無限制 {n_unlim}），共 {total_days} 天")
        out.extend(entries)
    return out


def scrape_lottery(page):
    """爬「玉山抽籤日期」的住宿日↔抽籤時間對照表。

    一律用公告值，不得用「住宿日前 31 天」之類的規律推算 ——
    實測住宿日與抽籤日的間隔是 28～31 天不等（遇假日順延），而且同一天有
    09:00／12:00／15:00 多個時段，光靠日期規律也推不出時段。
    推算錯一天，使用者就錯過整個抽籤週期。查無資料時前端顯示「尚未公告」。
    """
    page.goto(LOTTERY_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1200)

    lottery = []
    for r in _grid_rows(page):
        if len(r) < 2 or "住宿日" in r[0]:
            continue
        d = re.match(r'(\d{4})/(\d{2})/(\d{2})', r[0].strip())
        t = re.search(r'(\d{4})/(\d{2})/(\d{2})\s+(\d{2}:\d{2})[~～](\d{2}:\d{2})', r[1])
        if not (d and t):
            continue
        lottery.append({
            "stay_date": f"{d.group(1)}-{d.group(2)}-{d.group(3)}",
            "draw_date": f"{t.group(1)}-{t.group(2)}-{t.group(3)}",
            "draw_start": t.group(4),
            "draw_end": t.group(5),
        })
    # 抽籤適用範圍：直接從頁面敘述解析「…」內的項目，不寫死在程式裡。
    # 前端用它判斷某條單日往返路線要不要顯示抽籤時間 ——
    # 官方若新增或移除適用對象，這裡會跟著變。
    # 只取「…抽籤日期查詢」這句敘述裡的項目。用前 400 字會把頁尾的
    # 「臺灣登山申請一站式服務網」也撈進來，那不是抽籤對象。
    scope = page.evaluate("""() => {
        const t = document.body.innerText.replace(/\\s+/g, ' ');
        const i = t.indexOf('抽籤日期查詢');
        if (i < 0) return [];
        const seg = t.slice(Math.max(0, i - 200), i);
        return (seg.match(/「([^」]+)」/g) || []).map(x => x.replace(/[「」]/g, ''));
    }""")
    if scope:
        print(f"  抽籤適用範圍：{'、'.join(scope)}")

    lottery.sort(key=lambda x: x["stay_date"])
    print(f"  抽籤日期：{len(lottery)} 筆"
          + (f"，涵蓋住宿日 {lottery[0]['stay_date']} ~ {lottery[-1]['stay_date']}" if lottery else ""))
    return {"draws": lottery, "scope": scope}


def scrape():
    huts_result = []
    huts_next_result = []
    forest_result = []
    forest_next_result = []
    taroko_result = []
    taroko_next_result = []
    snow_result = []
    snow_next_result = []
    now = datetime.now(TW)
    next_year, next_month = next_month_year(now.year, now.month)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        detail_page = browser.new_page()

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(500)
        for hut in HUTS:
            result = safe_scrape(hut["name"], lambda h=hut: scrape_hut(page, detail_page, h["value"], h["name"]),
                                 {"name": hut["name"], "mountain": MOUNTAIN, "type": "未知",
                                  "capacity_weekday_bed": None, "capacity_weekend_bed": None,
                                  "capacity_weekday_tent": None, "capacity_weekend_tent": None, "days": []})
            huts_result.append(result)

        # 玉山系統額外多抓「下個月」一次，讓前端可以切換月份查看
        # #con_lbDownMonth 會把日曆往後翻一個月，且此狀態會在同一個 session 內
        # 跨山屋切換時持續有效，所以只需點一次，再把所有山屋重新查詢一遍即可
        with page.expect_response(lambda r: "bed_6.aspx" in r.url, timeout=20000):
            page.click("#con_lbDownMonth")
        page.wait_for_timeout(500)
        for hut in HUTS:
            result = safe_scrape(hut["name"] + "（下個月）", lambda h=hut: scrape_hut(page, detail_page, h["value"], h["name"]),
                                 {"name": hut["name"], "mountain": MOUNTAIN, "type": "未知",
                                  "capacity_weekday_bed": None, "capacity_weekend_bed": None,
                                  "capacity_weekday_tent": None, "capacity_weekend_tent": None, "days": []})
            huts_next_result.append(result)

        page.goto(FOREST_URL, wait_until="networkidle")
        page.wait_for_timeout(500)
        for hut in FOREST_HUTS:
            result = safe_scrape(hut["name"] + "",
                                 lambda h=hut: scrape_forest_hut(page, h["value"], h["name"], now.year, now.month),
                                 {"name": hut["name"], "days": []})
            forest_result.append(result)

        # 林業及自然保育署系統（嘉明湖／向陽／天池／檜谷）同樣多抓一次「下個月」
        with page.expect_response(lambda r: "bed_0.aspx" in r.url, timeout=20000):
            page.click("#con_lbDownMonth")
        page.wait_for_timeout(500)
        for hut in FOREST_HUTS:
            result = safe_scrape(hut["name"] + "（下個月）",
                                 lambda h=hut: scrape_forest_hut(page, h["value"], h["name"], next_year, next_month),
                                 {"name": hut["name"], "days": []})
            forest_next_result.append(result)

        page.goto(TAROKO_URL, wait_until="networkidle")
        page.wait_for_timeout(500)
        for hut in TAROKO_HUTS:
            result = safe_scrape(hut["name"] + "",
                                 lambda h=hut: scrape_progress_hut(page, TAROKO_URL, h["value"], h["name"], now.year, now.month),
                                 {"name": hut["name"], "days": []})
            taroko_result.append(result)

        # 太魯閣系統同樣多抓一次「下個月」
        with page.expect_response(lambda r: "bed_4.aspx" in r.url, timeout=20000):
            page.click("#con_lbDownMonth")
        page.wait_for_timeout(500)
        for hut in TAROKO_HUTS:
            result = safe_scrape(hut["name"] + "（下個月）",
                                 lambda h=hut: scrape_progress_hut(page, TAROKO_URL, h["value"], h["name"], next_year, next_month),
                                 {"name": hut["name"], "days": []})
            taroko_next_result.append(result)

        page.goto(SNOW_URL, wait_until="networkidle")
        page.wait_for_timeout(500)
        for hut in SNOW_HUTS:
            result = safe_scrape(hut["name"] + "",
                                 lambda h=hut: scrape_progress_hut(page, SNOW_URL, h["value"], h["name"], now.year, now.month),
                                 {"name": hut["name"], "days": []})
            snow_result.append(result)

        # 雪霸系統同樣多抓一次「下個月」
        with page.expect_response(lambda r: "bed_1.aspx" in r.url, timeout=20000):
            page.click("#con_lbDownMonth")
        page.wait_for_timeout(500)
        for hut in SNOW_HUTS:
            result = safe_scrape(hut["name"] + "（下個月）",
                                 lambda h=hut: scrape_progress_hut(page, SNOW_URL, h["value"], h["name"], next_year, next_month),
                                 {"name": hut["name"], "days": []})
            snow_next_result.append(result)

        # 公告類資料：封園與抽籤時間。包在 safe_scrape 裡，
        # 這兩項失敗不該讓整批名額資料白跑 —— 名額是主資料，公告是加值。
        closures = safe_scrape("封園公告", lambda: scrape_closures(page), [])
        lot = safe_scrape("抽籤日期", lambda: scrape_lottery(page), {"draws": [], "scope": []})
        permits = safe_scrape("路線證件", lambda: scrape_permits(page), {})
        route_cur, route_next = safe_scrape(
            "單日往返路線",
            lambda: scrape_route_quota(page, now.year, now.month, next_year, next_month),
            ([], []))
        trail_quota = safe_scrape(
            "路線人數限制",
            lambda: scrape_trail_quota(page, now.year, now.month, next_year, next_month),
            [])

        browser.close()

    return {
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "closures": closures,
        "lottery": lot.get("draws", []),
        "lottery_scope": lot.get("scope", []),
        "permits": permits,
        "route_quota": {"year": now.year, "month": now.month, "routes": route_cur},
        "route_quota_next_month": {"year": next_year, "month": next_month, "routes": route_next},
        "trail_quota": trail_quota,
        "year": now.year,
        "month": now.month,
        "huts": huts_result,
        "huts_next_month": {
            "year": next_year,
            "month": next_month,
            "huts": huts_next_result,
        },
        "forest_huts": forest_result,
        "forest_huts_next_month": {
            "year": next_year,
            "month": next_month,
            "huts": forest_next_result,
        },
        "taroko_huts": taroko_result,
        "taroko_huts_next_month": {
            "year": next_year,
            "month": next_month,
            "huts": taroko_next_result,
        },
        "snow_huts": snow_result,
        "snow_huts_next_month": {
            "year": next_year,
            "month": next_month,
            "huts": snow_next_result,
        },
    }


DATA_KEYS = ["huts", "forest_huts", "taroko_huts", "snow_huts"]
NEXT_KEYS = ["huts_next_month", "forest_huts_next_month",
             "taroko_huts_next_month", "snow_huts_next_month"]


def count_days(data):
    """統計整份資料實際抓到的『天數總筆數』。
    只數節點數不夠——政府網站改版時常見的狀況是節點還在、但每個節點的 days 都空了。"""
    total = 0
    for k in DATA_KEYS:
        for hut in data.get(k, []):
            total += len(hut.get("days", []))
    for k in NEXT_KEYS:
        for hut in data.get(k, {}).get("huts", []):
            total += len(hut.get("days", []))
    return total


# ---------------------------------------------------------------------------
# 逐系統健檢
#
# 既有的 verify_before_write 只看「全站天數總量」，擋得住整批壞掉，擋不住這幾種
# 悄悄壞掉的狀況：
#   - safe_scrape 吞掉個別山屋的失敗，27 間少 3 間，總量仍遠高於門檻
#   - 政府網站改欄位名稱，天數與筆數都沒變，但每一格的內容都解析成空的
#   - 單一系統整個掛掉，但其他三個系統把總量撐住
# 因此改成逐系統統計，並把「解析出實際內容的比例」當成主要訊號。
#
# 四個系統的資料結構彼此不同，判斷「這一天有沒有真的解析到東西」的方式也不同：
#   玉山       day["status"] 有值
#   林業保育署  day["items"] 有元素
#   太魯閣／雪霸 day["fields"] 有鍵值
# ---------------------------------------------------------------------------

SYSTEM_KEYS = {
    "玉山": ("huts", "huts_next_month"),
    "林業保育署": ("forest_huts", "forest_huts_next_month"),
    "太魯閣": ("taroko_huts", "taroko_huts_next_month"),
    "雪霸": ("snow_huts", "snow_huts_next_month"),
}


def _day_has_content(day):
    """這一天是否真的解析到內容。空的不等於壞掉（可能真的沒開放），但整個系統
    全空就幾乎一定是解析壞了。"""
    if day.get("status") is not None:
        return True
    if day.get("items"):
        return True
    if day.get("fields"):
        return True
    return False


def _vocabulary(days):
    """收集這個系統實際出現過的欄位名稱／狀態字串。

    政府網站改用字（例如「餘額」改成別的詞）時，天數與筆數都不會變，只有這份
    字彙會變。先把它記錄下來，累積幾天的實際波動後才有依據設白名單。
    """
    vocab = set()
    for day in days:
        if day.get("status") is not None:
            vocab.add(str(day["status"]))
        for item in day.get("items") or []:
            if item.get("label"):
                vocab.add(str(item["label"]))
        for key in (day.get("fields") or {}):
            vocab.add(str(key))
    return sorted(vocab)


def health_report(data):
    """產生逐系統健檢報表。只描述現況，不做判斷。

    本月與次月分開統計：兩者由不同的爬取流程取得，會各自壞掉。
    若合併計算，單月整個消失時比例仍有五成，剛好躲過所有門檻。
    """
    report = {"updated_at": data.get("updated_at"), "systems": {}}
    for label, (cur_key, next_key) in SYSTEM_KEYS.items():
        cur_huts = list(data.get(cur_key, []))
        next_huts = list(data.get(next_key, {}).get("huts", []))
        cur_days = [d for h in cur_huts for d in h.get("days", [])]
        next_days = [d for h in next_huts for d in h.get("days", [])]
        all_days = cur_days + next_days
        with_content = sum(1 for d in all_days if _day_has_content(d))
        report["systems"][label] = {
            "山屋數": len(cur_huts),
            "本月天數": len(cur_days),
            "次月天數": len(next_days),
            "天數": len(all_days),
            "有內容天數": with_content,
            "有內容比例": round(with_content / len(all_days), 3) if all_days else 0.0,
            "字彙": _vocabulary(all_days),
        }
    return report


def check_health(report, previous_path="health.json"):
    """比對上一次的健檢報表，明確壞掉就讓排程失敗。

    刻意只擋「幾乎不可能是正常波動」的狀況。山屋會季節性關閉、名額會歸零、
    颱風會封園，門檻設太緊會天天誤報，然後就會開始無視告警 —— 那比沒有告警更糟。
    容忍區間要等累積幾天的實際資料後再收緊，現階段先讓報表進版控累積觀察。
    """
    print("\n===== 逐系統健檢 =====")
    for label, s in report["systems"].items():
        print(f"  {label:<6} 山屋 {s['山屋數']:>3} 間｜本月 {s['本月天數']:>5} 天"
              f"／次月 {s['次月天數']:>5} 天｜有內容 {s['有內容天數']:>5}"
              f"（{s['有內容比例']:.0%}）｜字彙 {len(s['字彙'])} 種")

    previous = None
    if os.path.exists(previous_path):
        try:
            with open(previous_path, encoding="utf-8") as f:
                previous = json.load(f)
        except (json.JSONDecodeError, OSError):
            print("  （讀不到上次的健檢報表，本次只輸出現況）")

    problems = []
    for label, s in report["systems"].items():
        prev = (previous or {}).get("systems", {}).get(label)

        # 這個系統整個消失
        if s["山屋數"] == 0 and (prev is None or prev.get("山屋數", 0) > 0):
            problems.append(f"{label}：山屋數歸零")
            continue

        # 節點還在但一天都沒抓到。本月與次月分開判斷，避免其中一邊
        # 整個消失時被另一邊的數量掩蓋過去。
        for span in ("本月天數", "次月天數"):
            if s[span] == 0 and (prev or {}).get(span, 0) > 0:
                problems.append(
                    f"{label}：{span}歸零（上次 {prev[span]} 天，節點還在但沒有日期資料）")
        if s["天數"] == 0 and (prev is None or prev.get("天數", 0) > 0):
            problems.append(f"{label}：天數歸零（節點還在，但完全沒有日期資料）")
            continue

        # 節點與天數都在，但每一天都解析成空的 —— 典型的欄位改名
        if s["天數"] > 0 and s["有內容天數"] == 0:
            problems.append(f"{label}：{s['天數']} 天全部解析為空，欄位結構可能已變更")
            continue

        if not prev:
            continue

        # 山屋數腰斬。設 40% 是因為單一山屋維修下架屬正常，一次少掉四成不是
        if prev.get("山屋數", 0) > 0 and s["山屋數"] < prev["山屋數"] * 0.6:
            problems.append(f"{label}：山屋數 {prev['山屋數']} → {s['山屋數']}，減少逾四成")

        # 原本解析得出內容，現在幾乎全空
        if prev.get("有內容比例", 0) >= 0.5 and s["有內容比例"] < 0.1:
            problems.append(
                f"{label}：有內容比例 {prev['有內容比例']:.0%} → {s['有內容比例']:.0%}")

        # 字彙變化只提醒、不擋。這是 B 層白名單的觀察素材，現在還沒有基準可以判斷
        gone = set(prev.get("字彙", [])) - set(s["字彙"])
        added = set(s["字彙"]) - set(prev.get("字彙", []))
        if gone or added:
            print(f"  [注意] {label} 字彙有變動"
                  + (f"　消失：{'、'.join(sorted(gone))}" if gone else "")
                  + (f"　新增：{'、'.join(sorted(added))}" if added else ""))

    if problems:
        raise SystemExit("[中止] 健檢未過：\n  - " + "\n  - ".join(problems))

    print("  健檢通過")


def verify_before_write(new_data, previous_path="data.json", min_ratio=0.5):
    """寫檔前的防呆：抓到空資料或資料量驟降時直接失敗，不覆寫既有檔案。

    會擋下的狀況：
      1. 完全沒抓到任何天數（政府網站改版、被擋、全面逾時）
      2. 天數較上次驟降超過 50%（部分系統壞掉但爬蟲仍「成功」結束）

    對使用者而言，錯誤的名額比沒有名額更危險，所以寧可保留舊資料並讓排程失敗，
    也不要把壞資料蓋上去。
    """
    new_days = count_days(new_data)
    print(f"\n本次抓取天數總筆數：{new_days}")

    if new_days == 0:
        raise SystemExit("[中止] 本次完全沒抓到任何資料，保留既有 data.json 不覆寫")

    if not os.path.exists(previous_path):
        print("找不到既有 data.json，視為首次執行，直接寫入")
        return

    try:
        with open(previous_path, encoding="utf-8") as f:
            old_days = count_days(json.load(f))
    except Exception as e:
        print(f"[警告] 無法讀取既有 data.json（{type(e).__name__}），略過比對直接寫入")
        return

    print(f"上次抓取天數總筆數：{old_days}")
    if old_days > 0 and new_days < old_days * min_ratio:
        raise SystemExit(
            f"[中止] 資料量驟降（{old_days} → {new_days}，不足 {int(min_ratio*100)}%），"
            f"疑似來源網站異常，保留既有 data.json 不覆寫"
        )
    print("資料量檢查通過，寫入檔案")


def write_search_index(data, path="search-index.json"):
    """產生首頁搜尋用的輕量索引。

    使用者搜的是山名（玉山、雪山），資料裡存的是山屋名（排雲山莊、七卡山莊），
    兩者字面對不起來，因此每筆都帶上 aliases.py 維護的別名。
    """
    from aliases import HUT_ALIASES, NO_HUT_ROUTES

    SYSTEM_LABEL = {
        "huts": ("yushan", "玉山國家公園"),
        "snow_huts": ("snow", "雪霸國家公園"),
        "taroko_huts": ("taroko", "太魯閣國家公園"),
        "forest_huts": ("forest", "林業及自然保育署"),
    }

    index = []
    for key, (sys_key, sys_label) in SYSTEM_LABEL.items():
        for hut in data.get(key, []):
            name = hut["name"]
            kind = "營地" if ("營地" in name and "山屋" not in name and "山莊" not in name) else "山屋"
            index.append({
                "name": name,
                "alias": HUT_ALIASES.get(name, []),
                "system": sys_key,
                "systemLabel": sys_label,
                "type": kind,
                "url": f"huts.html?system={sys_key}&hut={quote(name)}",
            })

    # 單日往返路線：搜「玉山前峰」要能連到實際名額，而不是只回一行說明。
    # 這幾條有官方逐日名額，價值等同山屋，因此收進索引並指向名額頁。
    QUOTA_ALIASES = {
        "玉山前峰單日往返": ["玉山前峰", "前峰", "玉山前峰單攻"],
        "玉山線單日往返": ["玉山單攻", "玉山主峰單攻", "玉山線單攻", "玉山當日往返"],
        "庫哈諾辛山/關山單日往返": ["庫哈諾辛山", "關山", "庫哈諾辛"],
        "乙女瀑布單日往返": ["乙女瀑布", "乙女"],
        "瓦拉米單日往返": ["瓦拉米", "瓦拉米步道"],
    }
    scope = data.get("lottery_scope") or []
    for r in (data.get("route_quota") or {}).get("routes", []):
        name = r["name"]
        cap = r.get("capacity_weekday")
        note = f"每日 {cap} 人" if cap else "單日往返路線"
        if name in scope:
            note += "・抽籤制"
        index.append({
            "name": name,
            "alias": QUOTA_ALIASES.get(name, []),
            "system": "yushan",
            "systemLabel": "玉山國家公園",
            "type": "單日往返",
            "note": note,
            "url": f"huts.html?system=quota&hut={quote(name)}",
        })

    # 有人數上限的路線／登山口也收進索引，搜「錐麓古道」要能看到名額。
    # 無限制的不收 —— 沒有名額可查，點進去只會看到空日曆。
    TRAIL_ALIASES = {
        "錐麓古道": ["錐麓", "錐麓吊橋", "太魯閣錐麓"],
        "雪山登山口": ["雪山", "雪山主峰", "雪山單攻", "武陵雪山"],
        "武陵四秀登山口": ["武陵四秀", "桃山", "池有山", "品田山", "喀拉業山"],
        "大霸登山口": ["大霸尖山", "大霸", "小霸尖山"],
        "志佳陽登山口": ["志佳陽大山", "志佳陽"],
        "奇萊主、北峰線": ["奇萊主北", "奇萊北峰", "奇萊主峰"],
        "南湖大山線(因承載量異動，入園日期為114.7.1以後者適用)": ["南湖大山", "南湖"],
    }
    for e in data.get("trail_quota", []):
        if e.get("unlimited"):
            continue
        cap = e.get("capacity_weekday")
        note = f"每日 {cap} 人" if cap else ""
        note += f"・依{e.get('scope', '路線')}計算" if e.get("scope") else ""
        index.append({
            "name": e["name"],
            "alias": TRAIL_ALIASES.get(e["name"], []),
            "system": e.get("system", ""),
            "systemLabel": e.get("systemLabel", ""),
            "type": "人數限制",
            "note": note,
            "url": f"huts.html?system=trail&hut={quote(e['name'])}",
        })

    for r in NO_HUT_ROUTES:
        index.append({
            "name": r["name"],
            "alias": r["alias"],
            "system": None,
            "systemLabel": "免申請山屋",
            "type": "單攻路線",
            "note": r["note"],
            "url": None,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)

    size = os.path.getsize(path) / 1024
    no_alias = [x["name"] for x in index if x["system"] and not x["alias"]]
    print(f"\n搜尋索引：{len(index)} 筆，{size:.1f} KB")
    if no_alias:
        print(f"[提醒] 以下山屋尚無別名，山名搜不到：{'、'.join(no_alias)}")


def write_derived(data):
    """由 data.json 產生兩個衍生檔。

    這兩個檔一定要跟 data.json 同進同出：首頁讀 summary.json、查詢頁讀 data.json，
    只要其中一個沒更新，兩個頁面就會對同一份資料講出不同的更新時間
    （實際發生過：自動更新只提交了 data.json，首頁因此誤報「12 小時未更新」）。
    """
    # 輕量摘要（首頁用）。首頁只需要各系統的節點數與更新時間，
    # 不必為了 4 個數字就載入整份上百 KB 的完整資料。
    summary = {
        "updated_at": data["updated_at"],
        "counts": {
            "yushan": len(data["huts"]),
            "snow": len(data["snow_huts"]),
            "taroko": len(data["taroko_huts"]),
            "forest": len(data["forest_huts"]),
        },
    }
    summary["counts"]["total"] = sum(summary["counts"].values())
    with open("summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 搜尋索引（首頁搜尋框用）。只含搜尋必要欄位，體積遠小於完整資料，
    # 首頁才能維持「不載入 data.json」的輕量設計。
    write_search_index(data)


def write_health(report, path="health.json"):
    """把健檢報表寫進版控。

    這份檔案不供網站使用，目的是讓每次執行的統計進到 git 歷史，
    之後用 `git log -p health.json` 就能直接看出各系統的實際波動範圍，
    不必去翻 Actions 的執行紀錄。收緊告警門檻時需要的正是這份時間序列。
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def assert_timestamps_match():
    """確認三個檔案的 updated_at 一致，不一致就讓排程失敗而不是默默上線。

    首頁與查詢頁讀不同檔案，時間戳一旦分岔，使用者會在兩個頁面看到互相矛盾的
    更新時間，而「資料到底新不新」正是這個網站最需要講清楚的一件事。
    """
    with open("data.json", encoding="utf-8") as f:
        data_ts = json.load(f).get("updated_at")
    with open("summary.json", encoding="utf-8") as f:
        summary_ts = json.load(f).get("updated_at")
    if data_ts != summary_ts:
        raise SystemExit(
            f"[中止] data.json（{data_ts}）與 summary.json（{summary_ts}）更新時間不一致"
        )
    print(f"時間戳一致：{data_ts}")


if __name__ == "__main__":
    # --derive：不重新爬，只用現有的 data.json 重建 summary.json 與 search-index.json。
    # 用在衍生檔漏更新、需要補齊的時候，不必等下一次排程或重跑 20 分鐘的爬蟲。
    # --closures：只重抓封園公告，數秒完成。
    #
    # 為什麼要跟 --notices 分開：--notices 現在還包含 28 項路線人數限制的
    # 逐日資料，要跑好幾分鐘，而且只在全部完成後才寫檔 —— 中途逾時等於白跑。
    # 但封園解除是急事（颱風過了、路線恢復開放，站上還顯示禁止入園會擋到人），
    # 必須能單獨、快速地更新。
    if "--closures" in sys.argv:
        with open("data.json", encoding="utf-8") as f:
            data = json.load(f)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            new_closures = safe_scrape("封園公告", lambda: scrape_closures(page), [])
            browser.close()
        if not new_closures and data.get("closures"):
            print(f"  [保留] 本次抓取為空，維持既有 {len(data['closures'])} 筆")
        else:
            data["closures"] = new_closures
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            write_derived(data)
            assert_timestamps_match()
            n = sum(1 for c in new_closures if c.get("confirmed"))
            print(f"已更新封園公告：{len(new_closures)} 筆，其中確認禁止入園 {n} 筆")
        raise SystemExit(0)

    # --notices：只爬封園與抽籤兩張公告表，合併進現有的 data.json。
    # 公告的變動頻率與名額不同（颱風是突發的），而且只要幾秒鐘，
    # 不必為了更新一則封園公告重跑 20 分鐘的完整爬蟲。
    if "--notices" in sys.argv:
        with open("data.json", encoding="utf-8") as f:
            data = json.load(f)

        def keep_on_fail(key, value):
            """抓取失敗時保留既有資料，不要用空值覆蓋。

            實際踩過：路線證件那次抓取失敗，safe_scrape 回傳空字典，
            直接寫回去就把原本 8 筆已查證的證件資料清成 0 —— 
            輔助資料抓不到只是少一塊，把好資料蓋掉卻是把站上的內容弄壞。
            """
            empty = value is None or (hasattr(value, "__len__") and len(value) == 0)
            if empty and data.get(key):
                print(f"  [保留] {key} 本次抓取為空，維持既有 {len(data[key])} 筆")
                return
            data[key] = value
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            keep_on_fail("closures", safe_scrape("封園公告", lambda: scrape_closures(page), []))
            lot = safe_scrape("抽籤日期", lambda: scrape_lottery(page), {"draws": [], "scope": []})
            keep_on_fail("lottery", lot.get("draws", []))
            keep_on_fail("lottery_scope", lot.get("scope", []))
            keep_on_fail("permits", safe_scrape("路線證件", lambda: scrape_permits(page), {}))
            y, mo = data.get("year"), data.get("month")
            ny, nm = (y + 1, 1) if mo == 12 else (y, mo + 1)
            rc, rn = safe_scrape("單日往返路線",
                                 lambda: scrape_route_quota(page, y, mo, ny, nm), ([], []))
            data["route_quota"] = {"year": y, "month": mo, "routes": rc}
            data["route_quota_next_month"] = {"year": ny, "month": nm, "routes": rn}
            keep_on_fail("trail_quota", safe_scrape(
                "路線人數限制", lambda: scrape_trail_quota(page, y, mo, ny, nm), []))
            browser.close()
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        write_derived(data)
        assert_timestamps_match()
        print("已更新 data.json 的封園與抽籤公告")
        raise SystemExit(0)

    if "--derive" in sys.argv:
        with open("data.json", encoding="utf-8") as f:
            data = json.load(f)
        write_derived(data)
        assert_timestamps_match()
        report = health_report(data)
        write_health(report)
        check_health(report)
        print("已由現有 data.json 重建 summary.json、search-index.json 與 health.json")
        raise SystemExit(0)

    data = scrape()

    # 逐系統健檢：先跟上一次的報表比對，明確壞掉就中止，不覆寫既有資料。
    # 順序很重要 —— 要在寫檔之前跑，否則壞資料已經蓋上去了才發現沒有意義。
    report = health_report(data)
    check_health(report)

    # 寫檔前先驗證，避免壞資料覆蓋好資料
    verify_before_write(data)

    # 完整資料（查詢頁用）
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    write_derived(data)
    write_health(report)
    assert_timestamps_match()
    for hut in data["huts"]:
        print(f"{hut['name']}: 寫入 {len(hut['days'])} 天資料")
    for hut in data["huts_next_month"]["huts"]:
        print(f"{hut['name']}（下個月）: 寫入 {len(hut['days'])} 天資料")
    for hut in data["forest_huts"]:
        print(f"{hut['name']}: 寫入 {len(hut['days'])} 天資料")
    for hut in data["forest_huts_next_month"]["huts"]:
        print(f"{hut['name']}（下個月）: 寫入 {len(hut['days'])} 天資料")
    for hut in data["taroko_huts"]:
        print(f"{hut['name']}: 寫入 {len(hut['days'])} 天資料")
    for hut in data["taroko_huts_next_month"]["huts"]:
        print(f"{hut['name']}（下個月）: 寫入 {len(hut['days'])} 天資料")
    for hut in data["snow_huts"]:
        print(f"{hut['name']}: 寫入 {len(hut['days'])} 天資料")
    for hut in data["snow_huts_next_month"]["huts"]:
        print(f"{hut['name']}（下個月）: 寫入 {len(hut['days'])} 天資料")
