import json
import re
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

URL = "https://hike.taiwan.gov.tw/bed_6.aspx"
MOUNTAIN = "玉山"

HUTS = [
    {"value": "3", "name": "排雲山莊"},
    {"value": "727", "name": "觀高山屋"},
    {"value": "228", "name": "大水窟山屋"},
]

TW = timezone(timedelta(hours=8))


def parse_day_cell(cell):
    link = cell.query_selector("a")
    if not link:
        return None

    href = link.get_attribute("href") or ""
    m = re.search(r"sdate=(\d{4}-\d{2}-\d{2})", href)
    date = m.group(1) if m else None

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
    }


def _grab_int(text, label):
    m = re.search(label + r"\D*(\d+)", text)
    return int(m.group(1)) if m else None


def scrape_hut(page, hut_value, hut_name):
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

    return {
        "name": hut_name,
        "mountain": MOUNTAIN,
        "capacity_weekday_bed": cap_weekday_bed,
        "capacity_weekend_bed": cap_weekend_bed,
        "capacity_weekday_tent": cap_weekday_tent,
        "capacity_weekend_tent": cap_weekend_tent,
        "days": days,
    }


def scrape():
    huts_result = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(500)

        for hut in HUTS:
            result = scrape_hut(page, hut["value"], hut["name"])
            huts_result.append(result)

        browser.close()

    now = datetime.now(TW)
    return {
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "year": now.year,
        "month": now.month,
        "huts": huts_result,
    }


if __name__ == "__main__":
    data = scrape()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    for hut in data["huts"]:
        print(f"{hut['name']}: 寫入 {len(hut['days'])} 天資料")
