import feedparser, json, re, time, datetime as dt
from zoneinfo import ZoneInfo
from rapidfuzz import fuzz
from urllib.parse import urlparse

FEEDS = [
  "https://prtimes.jp/index.rdf",
  "https://www.atpress.ne.jp/rss/index.rdf",
]

JST = ZoneInfo("Asia/Tokyo")

def load_master():
    with open("data/jpx_master.json","r",encoding="utf-8") as f:
        return json.load(f)

def load_universe():
    with open("data/high_yield.json","r",encoding="utf-8") as f:
        return {r["code"]: r for r in json.load(f)}

def load_seen():
    with open("data/cache/seen.json","r",encoding="utf-8") as f:
        return set(json.load(f))

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", "", s or "")

def match_company(text, master):
    text_n = normalize_text(text)
    best = (None, 0)
    for r in master:
        score = fuzz.partial_ratio(r["key"], text_n)
        if score > best[1]:
            best = (r, score)
    return best if best[1] >= 85 else (None, 0)

def in_last_24h(entry):
    for k in ("published_parsed","updated_parsed","created_parsed"):
        if hasattr(entry, k) and getattr(entry, k):
            ts = dt.datetime(*getattr(entry,k)[:6], tzinfo=dt.timezone.utc).astimezone(JST)
            return (dt.datetime.now(JST) - ts) <= dt.timedelta(hours=24)
    return True

def entry_uid(e, feed_url: str) -> str:
    base = getattr(e, "id", None) or getattr(e, "link", None) or getattr(e, "title", "")
    host = urlparse(getattr(e, "link", "") or feed_url).netloc or "unknown"
    return f"{host}|{base}"

def run():
    master = load_master()
    universe = load_universe()
    seen = load_seen()

    hits = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries:
            if not in_last_24h(e):
                continue
            uid = entry_uid(e, url)
            if uid in seen:
                continue
            text = (e.title or "") + " " + (getattr(e, "summary", "") or "")
            rec, score = match_company(text, master)
            if rec and rec["code"] in universe:
                hits.append({
                    "uid": uid,
                    "code": rec["code"], "name": rec["name"],
                    "title": e.title, "link": e.link,
                    "summary": getattr(e,"summary",""),
                })
            time.sleep(0.05)

    with open("data/news_candidates.json","w",encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)
    print(f"News hits (unique): {len(hits)}")

if __name__ == "__main__":
    run()
