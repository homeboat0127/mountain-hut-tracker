#!/usr/bin/env python3
"""
把首頁熱門路線卡片上的數字，改由 huts.html 的路線資料「算出來」再寫回 index.html。

為什麼要這支程式：
  首頁卡片的里程／爬升／時數如果用手打，改了 huts.html 的路線點位或行程之後
  首頁不會跟著動，兩邊就會對不起來（實際發生過：奇萊和南湖那兩張卡飄掉了）。
  這支程式直接在瀏覽器裡載入 huts.html，呼叫頁面自己的 totalAscent()、
  longestDayHours()，用同一份程式碼算出同一組數字，因此不可能不同步。

規則：
  - 三個欄位固定為「來回里程 ｜ 來回累積爬升 ｜ 單日最長步行時數」，五張卡一致，
    方便橫向比較。爬升用累積值（每段正落差相加，且原路往返要把下切段加回來），
    不是起終點淨差 —— 用淨差會讓奇萊主北這種先下切再上攀的路線看起來比玉山輕鬆。
  - 任何一格算不出來就顯示「—」，不塞別的性質的內容進去充版面。
  - 數字一律取 variants[0]（各路線的主要走法，也就是官方建議天數那一條）。
  - 難度取該路線所有走法的區間（例如雪山 3、3、4 → 「難度 3～4／6」）。

用法：
  python3 sync_cards.py           # 寫回 index.html
  python3 sync_cards.py --check   # 只檢查有沒有不同步，不改檔（CI 用，不同步時 exit 1）
"""

import re
import sys
import json
import pathlib
import threading
import http.server
import socketserver
import functools

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
HUTS = ROOT / "huts.html"

# 首頁卡片的 route 參數 → 要在 huts.html 的 ROUTES 裡找的 key
CARD_ROUTES = ["yushan", "jiaming", "snow", "qilai", "nanhu"]

DASH = "—"

# 在頁面裡執行：用 huts.html 自己的函式算，不要在 Python 這邊重寫一份邏輯
# 順便把每個走法的官方登錄路線與難度撈出來，跟官方頁面的難度等級對帳
EXTRACT_VARIANTS_JS = """
() => {
  const out = [];
  for (const [key, r] of Object.entries(ROUTES)) {
    r.variants.forEach(v => out.push({
      route: key, variant: v.key, label: v.label,
      difficulty: v.difficultyLevel, officialRoute: v.officialRoute || null,
    }));
  }
  return out;
}
"""

EXTRACT_JS = """
(keys) => {
  const out = {};
  for (const key of keys) {
    const route = ROUTES[key];
    if (!route) { out[key] = null; continue; }
    const primary = route.variants[0];
    const levels = route.variants.map(v => v.difficultyLevel).filter(n => typeof n === 'number');
    out[key] = {
      label: route.label,
      distanceKm: typeof primary.distanceKm === 'number' ? primary.distanceKm : null,
      ascent: cumulativeAscent(primary.profile, primary.outAndBack, primary.extraAscent),
      hours: longestDayHours(primary.itinerary),
      diffMin: levels.length ? Math.min(...levels) : null,
      diffMax: levels.length ? Math.max(...levels) : null,
    };
  }
  return out;
}
"""


def serve(directory):
    """開一個本機伺服器，避免 file:// 下 fetch 被擋住影響頁面初始化。"""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def collect_stats():
    httpd, port = serve(ROOT)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{port}/huts.html", wait_until="domcontentloaded")
            page.wait_for_function("typeof ROUTES !== 'undefined' && typeof cumulativeAscent === 'function'",
                                   timeout=15000)
            stats = page.evaluate(EXTRACT_JS, CARD_ROUTES)
            variants = page.evaluate(EXTRACT_VARIANTS_JS)
            browser.close()
            if errors:
                print("[提醒] 頁面有 JS 錯誤（不一定影響取數，但值得看一下）：")
                for e in errors[:5]:
                    print("   ", e)
            return stats, variants
    finally:
        httpd.shutdown()


def fmt_stats(s):
    """三格固定順序、固定語意；算不出來就是「—」，不用別的東西補位。"""
    km = f"{s['distanceKm']}km" if s.get("distanceKm") else DASH
    ascent = f"累積爬升 {s['ascent']:,}m" if s.get("ascent") else f"累積爬升 {DASH}"
    hours = f"單日最長 {s['hours']}hr" if s.get("hours") else f"單日最長 {DASH}"
    return f"{km} ｜ {ascent} ｜ {hours}"


def fmt_tag(s):
    lo, hi = s.get("diffMin"), s.get("diffMax")
    if lo is None:
        return f"難度 {DASH}"
    return f"難度 {lo}／6" if lo == hi else f"難度 {lo}～{hi}／6"


def rewrite(html, stats):
    changes = []
    for key in CARD_ROUTES:
        s = stats.get(key)
        if not s:
            print(f"[警告] huts.html 找不到路線 {key}，該卡片維持原狀")
            continue

        card_re = re.compile(
            r'(<a class="card" href="huts\.html\?route=' + re.escape(key) + r'".*?</a>)',
            re.S,
        )
        m = card_re.search(html)
        if not m:
            print(f"[警告] index.html 找不到 {key} 的卡片，跳過")
            continue

        card = m.group(1)
        new_card = card

        want_tag, want_stats = fmt_tag(s), fmt_stats(s)

        def sub_one(text, pattern, new_inner, field):
            mm = re.search(pattern, text, re.S)
            if not mm:
                print(f"[警告] {key} 卡片缺少 {field}，跳過")
                return text
            if mm.group(1).strip() != new_inner:
                changes.append((s["label"], field, mm.group(1).strip(), new_inner))
            return text[:mm.start(1)] + new_inner + text[mm.end(1):]

        new_card = sub_one(new_card, r'<span class="peak-tag">(.*?)</span>', want_tag, "難度標籤")
        new_card = sub_one(new_card, r'<div class="peak-stats">(.*?)</div>', want_stats, "數據列")

        html = html[:m.start(1)] + new_card + html[m.end(1):]

    return html, changes


def check_difficulty(variants):
    """把站上顯示的難度跟官方「登山路線開放狀態」頁的難度等級對帳。

    站上聲明難度引用自官方分級表，兩者對不上就是展示了與原資料不符的資訊。
    這裡只提醒不中止 —— 官方有多份分級資料，要改哪一邊需要人判斷，
    但不能讓落差無聲無息地留著。
    """
    try:
        with open(ROOT / "data.json", encoding="utf-8") as f:
            permits = json.load(f).get("permits", {})
    except (OSError, json.JSONDecodeError):
        return
    if not permits:
        return

    gaps = []
    for v in variants:
        oc = v.get("officialRoute")
        info = permits.get(oc) if oc else None
        if not info or not info.get("difficulty"):
            continue
        m = re.search(r"(\d+)", info["difficulty"])
        if not m:
            continue
        official = int(m.group(1))
        if v.get("difficulty") != official:
            gaps.append((v["route"], v["label"], v["difficulty"], official, oc))

    if gaps:
        print("\n[提醒] 站上難度與官方頁面不一致（只提醒，不中止）：")
        for route, label, ours, official, oc in gaps:
            print(f"  {route}／{label}：站上 {ours} 級，官方「{oc}」為第 {official} 級")
    else:
        print("\n難度與官方頁面一致。")


def main():
    check_only = "--check" in sys.argv
    stats, variants = collect_stats()
    print("由 huts.html 算出的數字：")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    check_difficulty(variants)

    original = INDEX.read_text(encoding="utf-8")
    updated, changes = rewrite(original, stats)

    if not changes:
        print("\n首頁卡片與路線資料一致，不需更動。")
        return 0

    print("\n以下欄位與路線資料不同步：")
    for label, field, old, new in changes:
        print(f"  {label} {field}：{old}  →  {new}")

    if check_only:
        print("\n[--check] 偵測到不同步，未寫檔。請執行 python3 sync_cards.py 修正。")
        return 1

    INDEX.write_text(updated, encoding="utf-8")
    print(f"\n已更新 {INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
