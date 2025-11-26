# src/summarize.py の run() を差し替え

import json

POSITIVE_KEYWORDS = [
    "増配", "上方修正", "上方修", "最高益", "過去最高", "増益",
    "自社株買い", "自己株式取得", "株主還元強化",
    "大型受注", "長期契約", "新工場", "生産能力増強",
    "黒字転換", "通期予想据え置きで上期好調"
]

NEGATIVE_KEYWORDS = [
    "減配", "無配", "配当中止",
    "下方修正", "下方修", "業績悪化",
    "赤字", "最終赤字", "営業赤字", "不正会計",
    "リコール", "火災", "事故",
    "公募増資", "新株発行", "希薄化",
    "特別損失", "減損損失"
]

def judge_sentiment(text: str) -> str:
    """タイトル＋概要からざっくりプラス/マイナス/中立を判定（超シンプルなキーワードベース）"""
    if any(k in text for k in POSITIVE_KEYWORDS):
        return "plus"
    if any(k in text for k in NEGATIVE_KEYWORDS):
        return "minus"
    return "neutral"

def comment_for(sentiment: str) -> str:
    if sentiment == "plus":
        return "中長期ではプラス材料となる可能性があり、成長や株主還元にポジティブに働きそうです。"
    if sentiment == "minus":
        return "中長期ではややマイナス材料となる可能性があり、業績やバリュエーションへの注意が必要と考えられます。"
    return "中長期への影響は現時点では中立〜限定的と見ており、今後の継続的な開示や業績推移を注視したい内容です。"

def hashtags_for(sentiment: str) -> str:
    base_tags = ["日本株", "高配当株", "株式投資"]
    if sentiment == "plus":
        base_tags.append("好材料")
    elif sentiment == "minus":
        base_tags.append("悪材料")
    else:
        base_tags.append("材料整理")
    # ハッシュタグ文字列に変換
    return " ".join(f"#{t}" for t in base_tags)

def build_post(rec, limit_total=280):
    title = rec["title"]
    first = (rec.get("summary") or "").split("。")[0]
    header = f''
    main = f"{title}。{first}。"
    sentiment = judge_sentiment(title + " " + first)
    comment = comment_for(sentiment)
    tags = hashtags_for(sentiment)
    url = rec["link"]

    text = f"{header}{main}{comment} 詳しく: {url} {tags}"

    # 280文字を超える場合は末尾をカット
    if len(text) > limit_total:
        # URLとタグはできるだけ残したいので、本体だけ削る
        suffix = f" 詳しく: {url} {tags}"
        max_main = limit_total - len(header) - len(suffix) - 1
        trimmed_main = (main + comment)
        if len(trimmed_main) > max_main:
            trimmed_main = trimmed_main[: max_main - 1] + "…"
        text = f"{header}{trimmed_main}{suffix}"

    return text

def run():
    with open("data/news_candidates.json","r",encoding="utf-8") as f:
        items = json.load(f)

    # 1日1件のみ投稿する
    items = items[:1]

    out = [ {**r, "post": build_post(r)} for r in items ]
    with open("data/to_post.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Prepared posts: {len(out)}")

if __name__ == "__main__":
    run()
