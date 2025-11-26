import json
import re

def sanitize(text: str) -> str:
    """念のためHTMLタグなどを削る"""
    text = text or ""
    # <...> の簡易除去
    text = re.sub(r"<[^>]+>", "", text)
    # 余計な改行やタブをスペースに
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def build_post(rec, limit_total=140):
    title = sanitize(rec.get("title", ""))
    url = rec.get("link", "").strip()

    # コア部分：タイトル＋URL（必ずこれを優先）
    base = f"{title} {url}".strip()

    # まず「タイトル＋URL」が140文字を超える場合はタイトルだけ削る
    if len(base) > limit_total:
        # URLは必ず残したいので、タイトルをトリムする
        if not url:
            # URLがない異常ケースでは、タイトルだけでトリム
            if len(title) > limit_total:
                title = title[: limit_total - 1] + "…"
            return title

        max_title_len = limit_total - len(url) - 1  # 半角スペース分 -1
        if max_title_len <= 0:
            # さすがにないと思うが、URLだけ返す安全策
            return url[:limit_total]

        if len(title) > max_title_len:
            title = title[: max_title_len - 1] + "…"
        base = f"{title} {url}"

    # ここまでで「タイトル＋URL」は140文字以内に収まっている

    # ハッシュタグ（入るときだけ付ける）
    tags = "#日本株 #高配当株"
    if len(base) + 1 + len(tags) <= limit_total:
        text = f"{base} {tags}"
    else:
        text = base

    print("DEBUG tweet length:", len(text))
    return text

def run():
    # ニュース候補を読み込み
    with open("data/news_candidates.json", "r", encoding="utf-8") as f:
        items = json.load(f)

    # 1日1件だけ投稿
    items = items[:1]

    out = [{**r, "post": build_post(r)} for r in items]
    with open("data/to_post.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Prepared posts: {len(out)}")

if __name__ == "__main__":
    run()
