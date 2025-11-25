# src/high_yield.py（全部入れ替え）

import os, json

def build_universe():
    os.makedirs("data", exist_ok=True)
    manual_path = "data/high_yield_manual.json"
    out_path = "data/high_yield.json"

    if not os.path.exists(manual_path):
        raise FileNotFoundError(
            f"{manual_path} がありません。まず高配当銘柄リストを作成してください。"
        )

    with open(manual_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 念のため4%以上のものだけにフィルタ（yield記入ミス防止）
    hi = [r for r in data if r.get("yield") is not None and r["yield"] >= 0.04]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(hi, f, ensure_ascii=False, indent=2)

    print(f"Manual high-yield list loaded. Count (>=4%): {len(hi)}")

if __name__ == "__main__":
    build_universe()
