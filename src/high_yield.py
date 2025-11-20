import os, json, requests, time

API = "https://financialmodelingprep.com/api/v3"

def get_yield(symbol: str, key: str) -> float | None:
    url = f"{API}/key-metrics-ttm/{symbol}?apikey={key}"
    js = requests.get(url, timeout=30).json()
    if isinstance(js, list) and js:
        return (js[0].get("dividendYieldTTM") or js[0].get("dividend_yield_ttm"))
    return None

def build_universe():
    key = os.environ["FMP_API_KEY"]
    with open("data/jpx_master.json", "r", encoding="utf-8") as f:
        master = json.load(f)

    hi = []
    for i, row in enumerate(master, 1):
        symbol = f'{row["code"]}.T'
        try:
            y = get_yield(symbol, key)
        except Exception:
            y = None
        if y is not None and y >= 0.04:
            hi.append({**row, "symbol": symbol, "yield": y})
        if i % 25 == 0:
            time.sleep(1)

    with open("data/high_yield.json", "w", encoding="utf-8") as f:
        json.dump(hi, f, ensure_ascii=False, indent=2)
    print(f"High-yield (>=4%): {len(hi)} symbols")

if __name__ == "__main__":
    build_universe()
