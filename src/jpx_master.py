# src/jpx_master.py（download_latest_excel() を差し替え）

import pandas as pd, re, requests, io, json
from urllib.parse import urljoin

JPX_LIST_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"

def download_latest_excel():
    html = requests.get(JPX_LIST_URL, timeout=30).text
    # .xls でも .xlsx でも拾えるように
    m = re.search(r'href="([^"]+\.xls[x]?)"', html, flags=re.IGNORECASE)
    if not m:
        raise RuntimeError("JPXのExcelリンクが見つかりませんでした。")
    xurl = urljoin("https://www.jpx.co.jp", m.group(1))
    bin = requests.get(xurl, timeout=60).content

    ext = xurl.split("?")[0].split(".")[-1].lower()
    if ext == "xlsx":
        return pd.read_excel(io.BytesIO(bin), engine="openpyxl")
    else:
        # 既定では .xls → xlrd が必要
        return pd.read_excel(io.BytesIO(bin), engine="xlrd")
