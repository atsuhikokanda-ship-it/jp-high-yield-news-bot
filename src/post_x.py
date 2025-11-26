# src/post_x.py

import os, json, requests, time
from requests_oauthlib import OAuth1  # ★ 追加

# OAuth1.0a の4つの値を環境変数から取得
API_KEY = os.environ["X_API_KEY"]
API_SECRET = os.environ["X_API_SECRET"]
ACCESS_TOKEN = os.environ["X_ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]

SEEN_PATH = "data/cache/seen.json"

# 共通の auth オブジェクト
AUTH = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

def post(text):
    r = requests.post(
        "https://api.x.com/2/tweets",
        auth=AUTH,                   # ★ Authorizationヘッダではなく、authに指定
        json={"text": text},
        timeout=30
    )
    if not r.ok:
        print("X API error:", r.status_code, r.text)
        r.raise_for_status()
    return r.json()["data"]["id"]

def load_seen():
    with open(SEEN_PATH, "r", encoding="utf-8") as f:
        return set(json.load(f))

def save_seen(seen_set):
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen_set)), f, ensure_ascii=False)

def run():
    try:
        with open("data/to_post.json", "r", encoding="utf-8") as f:
            items = json.load(f)
    except FileNotFoundError:
        print("No to_post.json found → skip")
        return

    if not items:
        print("No posts today → skip")
        return

    seen = load_seen()
    posted = 0

    for r in items:
        try:
            tid = post(r["post"])
            url = f"https://x.com/i/web/status/{tid}"
            print("posted:", tid, url, r["title"])
            posted += 1
            if "uid" in r and r["uid"]:
                seen.add(r["uid"])
            time.sleep(2)
            break  # ★ 1件投稿したら終了
        except Exception as e:
            print("skip:", e)

    save_seen(seen)
    print("total posted:", posted)

if __name__ == "__main__":
    run()
