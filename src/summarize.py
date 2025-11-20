import json

def summarize_one(rec, limit=260):
    first = (rec.get("summary") or "").split("。")[0]
    msg = f'{rec["title"]}。{first}。詳しく: {rec["link"]}'
    return (msg[:limit] + "…") if len(msg) > limit else msg

def run():
    with open("data/news_candidates.json","r",encoding="utf-8") as f:
        items = json.load(f)
    out = [ {**r, "post": summarize_one(r)} for r in items[:5] ]  # 1日最大5件
    with open("data/to_post.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Prepared posts: {len(out)}")

if __name__ == "__main__":
    run()
