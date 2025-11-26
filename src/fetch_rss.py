import feedparser
import json
import re
import time
import datetime as dt
from zoneinfo import ZoneInfo
from rapidfuzz import fuzz
from urllib.parse import urlparse

FEEDS = [
    "https://prtimes.jp/index.rdf",
    "https://www.atpress.ne.jp/rss/index.rdf",
]

JST = ZoneInfo("Asia/Tokyo")


def normalize_name(s: str) -> str:
    """社名をあいまい一致用に正規化"""
    s = s or ""
    # 全角カッコ、空白、・などを削除
    s = re.sub(r"[（）\(\)\s・･　]", "", s)
    # よくある末尾の会社形態を削る
    s = re.sub(r"(株式会社|（株）|Co\.?,?Ltd\.?|ホールディングス|HD)$", "", s, flags=re.I)
    return s


def load_universe():
    """
    高配当ユニバース（= あなたのリスト）だけを読み込む。
    ここに載っている銘柄だけニュース対象。
    """
    with open("data/high_yield.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # あいまい一致用に key を追加（ファイルには書き戻さない）
    for r in data:
        r["key"] = normalize_name(r.get("name", ""))
    return data  # list


def load_seen():
    with open("data/cache/seen.json", "r", encoding="utf-8") as f:
        return set(json.load(f))


def in_last_24h(entry):
    for k in ("published_parsed", "updated_parsed", "created_parsed"):
        if hasattr(entry, k) and getattr(entry, k):
            ts = dt.datetime(*getattr(entry, k)[:6], tzinfo=dt.timezone.utc).astimezone(JST)
            return (dt.datetime.now(JST) - ts) <= dt.timedelta(hours=24)
    # タイムスタンプが取れない場合はいったん採用
    return True


def entry_uid(e, feed_url: str) -> str:
    base = getattr(e, "id", None) or getattr(e, "link", None) or getattr(e, "title", "")
    host = urlparse(getattr(e, "link", "") or feed_url).netloc or "unknown"
    return f"{host}|{base}"


def match_company(text: str, universe: list):
    """
    ニュース本文から、高配当ユニバースのどの銘柄に一番近いかを判定。
    → ユニバース外はそもそも対象にしない。
    """
    text_n = re.sub(r"\s+", "", text or "")
    best = (None, 0)
    for r in universe:
        score = fuzz.partial_ratio(r["key"], text_n)
        if score > best[1]:
            best = (r, score)
    # 閾値は必要に応じて調整（今は85）
    return best if best[1] >= 85 else (None, 0)


def run():
    universe = load_universe()   # ★ ここには「あなたの高配当リスト」だけが入る
    seen = load_seen()

    hits = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries:
            if not in_last_24h(e):
                continue

            uid = entry_uid(e, url)
            if uid in seen:
                continue  # 既に投稿済みならスキップ

            title = e.title or ""
            summary = getattr(e, "summary", "") or ""
            text = title + " " + summary

            rec, score = match_company(text, universe)
            if rec:
                hits.append({
                    "uid": uid,
                    "code": rec["code"],
                    "name": rec["name"],
                    "title": title,
                    "link": e.link,
                    "summary": summary,
                })
            time.sleep(0.05)

    with open("data/news_candidates.json", "w", encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)

    print(f"News hits (universe only): {len(hits)}")


if __name__ == "__main__":
    run()
