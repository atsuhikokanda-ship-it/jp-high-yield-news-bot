import os, json, requests, time, datetime as dt

API = "https://financialmodelingprep.com/stable"
KEY = os.environ["FMP_API_KEY"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}

# --- ユーティリティ ---
def _get(url, params=None):
    for i in range(3):  # 簡易リトライ
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == 2:
                raise
            time.sleep(1.5)

def _quote_price(symbol: str) -> float | None:
    js = _get(f"{API}/quote", {"symbol": symbol, "apikey": KEY})
    if isinstance(js, list) and js:
        # price or previousClose を順に採用
        p = js[0].get("price") or js[0].get("previousClose")
        return float(p) if p not in (None, "", 0) else None
    return None

def _dividend_yield_from_dividends(symbol: str) -> float | None:
    """
    1) /dividends の最新レコードに 'yield' があればそれを採用
    2) なければ過去365日の配当金を合計し、quote価格で割って利回り算出
    """
    js = _get(f"{API}/dividends", {"symbol": symbol, "apikey": KEY})
    if not js:
        return None

    # 1) 最新レコードの yield フィールド
    latest = js[0] if isinstance(js, list) else None
    if latest and isinstance(latest, dict):
        y = latest.get("yield") or latest.get("dividendYield")
        if y not in (None, "", 0):
            try:
                return float(y)
            except Exception:
                pass

    # 2) 直近365日の配当合計 ÷ 現値
    one_year_ago = dt.datetime.utcnow() - dt.timedelta(days=365)
    total_div = 0.0
    for row in js:
        # row例: { 'date': '2025-03-29', 'dividend': 30.0, ... }
        d = row.get("date") or row.get("paymentDate") or ""
        amt = row.get("dividend") or row.get("adjDividend") or row.get("adjustedDividend")
        if not d or amt in (None, "", 0):
            continue
        try:
            if dt.datetime.fromisoformat(d[:10]) >= one_year_ago:
                total_div += float(amt)
        except Exception:
            continue

    if total_div <= 0:
        return None

    px = _quote_price(symbol)
    if not px or px <= 0:
        return None

    return total_div / px  # ← 例えば 0.045 (= 4.5%)

def build_universe():
    # マスタ読込
    os.makedirs("data", exist_ok=True)
    with open("data/jpx_master.json", "r", encoding="utf-8") as f:
        master = json.load(f)

    hi = []
    cnt = 0
    for i, row in enumerate(master, 1):
        symbol = f'{row["code"]}.T'  # 日本株は多くが .T
        try:
            y = _dividend_yield_from_dividends(symbol)
        except Exception as e:
            # APIエラーはスキップして続行
            y = None

        if y is not None and y >= 0.04:
            hi.append({**row, "symbol": symbol, "yield": y})

        cnt += 1
        if i % 25 == 0:
            time.sleep(0.8)  # 無料枠対策でウェイト

    with open("data/high_yield.json", "w", encoding="utf-8") as f:
        json.dump(hi, f, ensure_ascii=False, indent=2)

    print(f"Checked: {cnt} symbols, High-yield (>=4%): {len(hi)}")
    # デバッグしやすいよう、上位数件をログ出力
    for s in hi[:10]:
        print(f' - {s["code"]}.T  yield≈{round(s["yield"]*100,2)}%  {s["name"]}')

if __name__ == "__main__":
    build_universe()
