import feedparser
import json
import re
import time
import datetime as dt
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

FEEDS = [
    "https://prtimes.jp/index.rdf",
    "https://www.atpress.ne.jp/rss/index.rdf",
]

JST = ZoneInfo("Asia/Tokyo")


def normalize_text(s: str) -> str:
    """ニュース本文用の簡易正規化（空白などを削る）"""
    s = s or ""
    s = re.sub(r"\s+", "", s)
    return s


def normalize_name(s: str) -> str:
    """社名を正規化（株式会社などを削る）"""
    s = s or ""
    # 全角カッコ、半角カッコ、空白、・などを除去
    s = re.sub(r"[（）\(\)\s・･　]", "", s)
    # よくある会社形態を末尾から削る
    s = re.sub(r"(株式会社|（株）|Co\.?,?Ltd\.?|ホールディングス|HD)$", "", s, flags=re.I)
    return s


def load_universe():
    """
    高配当ユニバース（＝あなたのリスト）だけを読み込む。
    ここに載っている企業だけニュース対象にする。
    """
    with open("data/high_yield.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for r in data:
        r["key"] = normalize_name(r.get("name", ""))
    return data  # list[dict]


def load_seen():
    with open("data/cache/seen.json", "r", encoding="utf-8") as f:
        return set(json.load(f))


def in_last_24h(entry):
    for k in ("published_parsed", "updated_parsed", "created_parsed"):
        if hasattr(entry, k) and getattr(entry, k):
            ts = dt.datetime(*getattr(entry, k)[:6], tzinfo=dt.timezone.utc).astimezone(JST)
            return (dt.datetime.now(JST) - ts) <= dt.timedelta(hours=24)
    # タイムスタンプが取れないものは一応対象にする
    return True


def entry_uid(e, feed_url: str) -> str:
    base = getattr(e, "id", None) or getattr(e, "link", None) or getattr(e, "title", "")
    host = urlparse(getattr(e, "link", "") or feed_url).netloc or "unknown"
    return f"{host}|{base}"


def match_company(text: str, universe: list):
    """
    正規化した本文に、正規化した社名(key)が「そのまま含まれている」場合だけ採用。
    fuzzy は使わない。
    """
    text_n = normalize_text(text)
    hits = []

    for r in universe:
        key = r.get("key")
        if not key:
            continue
        if key in text_n:
            hits.append(r)

    if not hits:
        return None

    # 万が一複数ヒットした場合は、社名が一番長いものを選ぶ（より固有名詞っぽい方）
    hits.sort(key=lambda x: len(x.get("key", "")), reverse=True)
    return hits[0]


def run():
    universe = load_universe()   # あなたの高配当リストだけ
    seen = load_seen()

    hits = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries:
            if not in_last_24h(e):
                continue

            uid = entry_uid(e, url)
            if uid in seen:
                continue  # すでに投稿済みならスキップ

            title = e.title or ""
            summary = getattr(e, "summary", "") or ""
            text = title + " " + summary

            rec = match_company(text, universe)
            if rec:
                hits.append({
                    "uid": uid,
                    "code": rec["code"],
                    "name": rec["name"],
                    "title": title,
                    "link": e.link,
                    "summary": summary,
                })
                # デバッグ用にログ
                print(f"HIT: {rec['code']} {rec['name']} ← {title}")

            time.sleep(0.05)

    with open("data/news_candidates.json", "w", encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)

    print(f"News hits (universe strict): {len(hits)}")


if __name__ == "__main__":
    run()
