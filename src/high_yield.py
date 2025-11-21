# src/high_yield.py
import os, json, requests, time, datetime as dt

API = "https://financialmodelingprep.com/stable"
KEY = os.environ["FMP_API_KEY"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}

def _get(url, params=None):
    for i in range(3):
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
        p = js[0].get("price") or js[0].get("previousClose")
        return float(p) if p not in (None, "", 0) else None
    return None

def _dividend_yield(symbol: str) -> float | None:
    # /dividends → 最新の yield があれば採用。なければ365日合計÷価格
    js = _get(f"{API}/dividends", {"symbol": symbol, "apikey": KEY})
    if not js:
        return None
    latest = js[0] if isinstance(js, list) else None
    if latest and isinstance(latest, dict):
        y = latest.get("yield") or latest.get("dividendYield")
        if y not in (None, "", 0):
            try:
                return float(y)
            except Exception:
                pass
    one_year_ago = dt.datetime.utcnow() - dt.timedelta(days=365)
    total_div = 0.0
    for row in js:
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
    return total_div / px

def build_universe():
    os.makedirs("data", exist_ok=True)
    
    # ★ ここから追加：日曜以外は実行しない（JST基準）
    today_jst = dt.datetime.utcnow() + dt.timedelta(hours=9)
    if today_jst.weekday() != 6:  # Monday=0 ... Sunday=6
        print("Skip building universe today (run weekly on Sunday).")
        return
    # ★ 追加ここまで
    
    # マスタ
    with open("data/jpx_master.json", "r", encoding="utf-8") as f:
        master = json.load(f)

    # 旧キャッシュ
    cache_path = "data/high_yield.json"
    old = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            for r in json.load(f):
                old[r["code"]] = r

    # 更新ポリシー設定
    today = dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=9)))  # JST相当
    weekday = today.weekday()  # Mon=0 ... Sun=6
    full_rebuild = (weekday == 6)  # 日曜はフル
    # ローリング分割: 証券コード%7 == weekday のものだけ当日更新
    def should_update(code: str) -> bool:
        if full_rebuild:
            return True
        try:
            return int(code) % 7 == weekday
        except Exception:
            return False

    updated = 0
    result = []
    for i, row in enumerate(master, 1):
        code = row["code"]
        symbol = f'{code}.T'
        # 更新対象かどうか
        if should_update(code):
            try:
                y = _dividend_yield(symbol)
            except Exception:
                y = None
            rec = {**row, "symbol": symbol}
            if y is not None:
                rec["yield"] = y
                rec["last_updated"] = today.isoformat()
            else:
                # APIで取れなかった場合は旧値があれば引き継ぐ
                if code in old and "yield" in old[code]:
                    rec["yield"] = old[code]["yield"]
                    rec["last_updated"] = old[code].get("last_updated")
            result.append(rec)
            updated += 1
            if i % 25 == 0:
                time.sleep(0.8)
        else:
            # 当日は更新しない → キャッシュ優先
            if code in old:
                result.append(old[code])
            else:
                # キャッシュ未収載なら最低限の骨格のみ
                result.append({**row, "symbol": symbol})

    # フィルタ（>=4%）
    hi = [r for r in result if r.get("yield") is not None and r["yield"] >= 0.04]

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"{'FULL' if full_rebuild else 'PARTIAL'} update; checked: {updated} / {len(master)}")
    print(f"High-yield (>=4%): {len(hi)}")
    for s in hi[:10]:
        ypct = round(s['yield']*100, 2)
        print(f' - {s["code"]}.T  yield≈{ypct}%  {s["name"]}')

if __name__ == "__main__":
    build_universe()
