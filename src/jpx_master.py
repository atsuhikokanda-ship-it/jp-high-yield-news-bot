# src/jpx_master.py
import pandas as pd, re, requests, io, json

JPX_LIST_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"

def download_latest_excel():
    html = requests.get(JPX_LIST_URL, timeout=30).text
    m = re.search(r'href="([^"]+\.xls[^"]*)"', html)
    if not m:
        raise RuntimeError("JPXのExcelリンクが見つかりませんでした。")
    xurl = "https://www.jpx.co.jp" + m.group(1)
    bin = requests.get(xurl, timeout=60).content
    return pd.read_excel(io.BytesIO(bin))

def normalize_name(s: str) -> str:
    import re
    s = re.sub(r"[（）\(\)\s・･　]", "", s or "")
    s = re.sub(r"(株式会社|（株）|Co\.?,?Ltd\.?|ホールディングス|HD)$", "", s, flags=re.I)
    return s

def build_master():
    df = download_latest_excel()
    code_col = [c for c in df.columns if "コード" in c][0]
    name_col = [c for c in df.columns if ("銘柄名" in c or "会社名" in c)][0]
    out = []
    for _, r in df.iterrows():
        code = str(r[code_col]).split(".")[0].zfill(4)[:4]
        if not code.isdigit(): 
            continue
        name = str(r[name_col])
        out.append({"code": code, "name": name, "key": normalize_name(name)})
    with open("data/jpx_master.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    build_master()
