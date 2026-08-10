#!/usr/bin/env python3
"""把目前的頁面複製一份到 preview/，產生可用手機開的預覽網址。

為什麼需要這個：
  改版面時光看桌機瀏覽器不夠 —— 手機上的實際觀感（字級、格子寬度、
  觸控目標大小）只有真的用手機開才知道。但直接改正式站等於拿使用者當測試對象。

做法：
  preview/ 底下放一份獨立的 HTML，資料檔仍指向根目錄的 data.json，
  因此預覽站與正式站看到的是同一份資料，差別只在版面與程式碼。
  正式站的 index.html / huts.html 完全不受影響 —— 兩邊是不同檔案，
  預覽站壞掉不會波及正式站。

網址：
  正式站　https://homeboat0127.github.io/mountain-hut-tracker/
  預覽站　https://homeboat0127.github.io/mountain-hut-tracker/preview/

用法：
  python3 make_preview.py          # 產生／更新預覽站
  python3 make_preview.py --clean  # 移除預覽站
"""

import re
import sys
import shutil
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
PREVIEW = ROOT / "preview"
PAGES = ["index.html", "huts.html"]

# 這些是放在根目錄的資料檔，預覽站要往上一層取，
# 才能跟正式站看同一份資料，不必複製一份 1.2 MB 的 data.json
DATA_FILES = ["data.json", "summary.json", "search-index.json"]

BANNER = """<div style="position:sticky;top:0;z-index:999;background:#8a5f16;color:#fff;
padding:7px 12px;font-size:12.5px;line-height:1.6;text-align:center;
font-family:-apple-system,'PingFang TC',sans-serif;">
🔧 預覽版 — 這是測試中的版面，不是正式網站。
<a href="../index.html" style="color:#ffe9bf;">前往正式站 →</a></div>
"""


def build():
    PREVIEW.mkdir(exist_ok=True)
    for name in PAGES:
        src = ROOT / name
        if not src.exists():
            print(f"[跳過] 找不到 {name}")
            continue
        html = src.read_text(encoding="utf-8")

        # 資料檔：優先讀 preview/ 自己的一份，沒有才回退到根目錄。
        #
        # 為什麼要有這個回退：預覽站原本一律讀 ../data.json（正式站那份），
        # 結果只要新功能需要新的資料欄位，預覽站就測不出來 ——
        # 實際踩過：單日往返名額的 route_quota 欄位在正式站的 data.json 還不存在，
        # 預覽站看起來像是功能壞掉，其實是資料沒跟上。
        # 資料結構沒變時 preview/ 不會有副本，兩站共用同一份，不佔空間。
        for f in DATA_FILES:
            html = html.replace(
                f"fetch('{f}')",
                f"fetch('{f}').then(function(r){{return r.ok?r:fetch('../{f}');}})")

        # 頁面之間的連結留在預覽站內部，才不會點一下就跳回正式站
        # （huts.html / index.html 都已複製到 preview/，相對連結本來就會對）

        # 加上明顯的預覽標示，避免把預覽站誤當正式站
        html = html.replace("<body>", "<body>\n" + BANNER, 1)
        html = html.replace("<title>", "<title>[預覽] ", 1)

        (PREVIEW / name).write_text(html, encoding="utf-8")
        print(f"  已產生 preview/{name}")

    # 不需要 robots 索引預覽站
    (PREVIEW / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    print("\n預覽網址：https://homeboat0127.github.io/mountain-hut-tracker/preview/")
    print("正式網址：https://homeboat0127.github.io/mountain-hut-tracker/")
    print("\n提醒：預覽站與正式站讀同一份 data.json，資料一致，差別只在版面與程式碼。")


def clean():
    if PREVIEW.exists():
        shutil.rmtree(PREVIEW)
        print("已移除 preview/")
    else:
        print("preview/ 不存在，不需移除")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean()
    else:
        build()
