# src/jpx_master.py（全部差し替え）
import os, io, re, json, requests, pandas as pd
from urllib.parse import urljoin

JPX_LIST_PAGE = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}

def normalize_name(s: str) -> str:
    s = re.sub(r"[（）\(\)\s・･　]", "", s or "")
    s = re.sub(r"(株式会社|（株）|Co\.?,?Ltd\.?|ホールディングス|HD)$", "", s, flags=re.I)
    return s

def try_jpx_excel():
    print("[JPX] ページを解析してExcelリンクを探します…")
    html = requests.get(JPX_LIST_PAGE, headers=HEADERS, timeout=60).text
    m = re.search(r'href="([^"]+\.xls[x]?)"', html, flags=re.IGNORECASE)
    if not m:
        raise RuntimeError("JPXのExcelリンクが見つかりませんでした。")
    xurl = urljoin("https://www.jpx.co.jp", m.group(1))
    print(f"[JPX] Excel URL: {xurl}")
    bin = requests.get(xurl, headers=HEADERS, timeout=120).content
    ext = xurl.split("?")[0].split(".")[-1].lower()
    if ext == "xlsx":
        df = pd.read_excel(io.BytesIO(bin), engine="openpyxl")
    else:
        df = pd.read_excel(io.BytesIO(bin), engine="xlrd")
    # 代表的な列名を推定
    code_col = [c for c in df.columns if "コード" in c][0]
    name_col = [c for c in df.columns if ("銘柄名" in c or "会社名" in c)][0]
    out = []
    for _, r in df.iterrows():
        code_raw = str(r[code_col]).strip()
        code4 = re.match(r"(\d{4})", code_raw)
        if not code4:
            continue
        code = code4.group(1)
        name = str(r[name_col]).strip()
        out.append({"code": code, "name": name, "key": normalize_name(name)})
    print(f"[JPX] 取得件数: {len(out)}")
    if len(out) < 10:
        raise RuntimeError("JPX Excelから十分な件数を取得できませんでした。")
    return out

def fallback_from_fmp():
    """JPXが失敗した場合の保険：FMPの全銘柄リストから .T を抽出"""
    import os
    key = os.environ.get("FMP_API_KEY")
    if not key:
        raise RuntimeError("FMP_API_KEY が未設定のためフォールバック不可。")
    url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={key}"
    print("[FMP] stock/list を取得中…")
    js = requests.get(url, headers=HEADERS, timeout=120).json()
    out = []
    for r in js:
        sym = r.get("symbol") or ""
        name = r.get("name") or ""
        # 日本株は多くが .T 末尾（TOPIX銘柄は網羅される）
        if sym.endswith(".T"):
            # 先頭4桁の数字をコードとして採用
            m = re.match(r"(\d{4})\.T$", sym)
            if not m:
                continue
            code = m.group(1)
            out.append({"code": code, "name": name, "key": normalize_name(name)})
    print(f"[FMP] 取得件数 (.T): {len(out)}")
    if len(out) < 10:
        raise RuntimeError("FMPフォールバックでも十分な件数が取得できませんでした。")
    return out

def build_master():
    os.makedirs("data", exist_ok=True)
    try:
        rows = try_jpx_excel()
    except Exception as e:
        print(f"[JPX] 失敗: {e}")
        print("[JPX] → FMPフォールバックに切り替えます")
        rows = fallback_from_fmp()
    with open("data/jpx_master.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved data/jpx_master.json ({len(rows)} rows)")

if __name__ == "__main__":
    build_master()
