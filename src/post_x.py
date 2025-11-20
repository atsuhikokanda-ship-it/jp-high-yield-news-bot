import os, json, requests, time

X_TOKEN = os.environ["X_BEARER_TOKEN"]
SEEN_PATH = "data/cache/seen.json"

def post(text):
    r = requests.post(
        "https://api.x.com/2/tweets",
        headers={"Authorization": f"Bearer {X_TOKEN}", "Content-Type":"application/json"},
        json={"text": text}, timeout=30
    )
    r.raise_for_status()
    return r.json()["data"]["id"]

def load_seen():
    with open(SEEN_PATH,"r",encoding="utf-8") as f:
        return set(json.load(f))

def save_seen(seen_set):
    with open(SEEN_PATH,"w",encoding="utf-8") as f:
        json.dump(sorted(list(seen_set)), f, ensure_ascii=False)

def run():
    try:
        with open("data/to_post.json","r",encoding="utf-8") as f:
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
            print("posted:", tid, r["title"])
            posted += 1
            if "uid" in r and r["uid"]:
                seen.add(r["uid"])
            time.sleep(2)
        except Exception as e:
            print("skip:", e)

    save_seen(seen)
    print("total posted:", posted)

if __name__ == "__main__":
    run()
