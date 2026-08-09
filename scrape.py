import json
import re
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

        browser.close()

    return {
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
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


if __name__ == "__main__":
    data = scrape()
    # 完整資料（查詢頁用）
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
