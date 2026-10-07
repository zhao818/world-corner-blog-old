#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拆书脚本：把《精神现象学》英文全文按主章节边界切成 17 个章节文件
用法: python split_book.py
输出: chapters/01_*.txt ... chapters/17_*.txt  +  plan.json (章节清单)
"""
import os, json, re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\Users\zhaot\Downloads\Hegel\Hegel_Phenomenology_of_Spirit_EN.txt"
CH_DIR = os.path.join(SCRIPT_DIR, "chapters")
PLAN = os.path.join(SCRIPT_DIR, "plan.json")

BOUNDS = [
    ("导论 Introduction",                  22,   2793),
    ("A. 意识 Consciousness",             2793,  5090),
    ("B. 自我意识 Self-Consciousness",     5090,  6783),
    ("V. 理性 Reason（引论）",             6783,  7100),
    ("A. 观察的理性 Observing Reason",     7100, 10276),
    ("B. 理性的现实化 Actualization",     10276, 11489),
    ("C. 自在而自为的个体性 Individuality", 11489, 12798),
    ("VI. 精神 Spirit（引论）",            12798, 12944),
    ("A. 真实的精神·伦理秩序 Ethical Order", 12944, 14337),
    ("B. 自我异化的精神·教化 Culture",     14337, 14466),
    ("I. 异化精神的世界 World of Self-Alienation", 14466, 15992),
    ("II. 启蒙 Enlightenment",             15992, 17330),
    ("III. 绝对自由与恐怖 Absolute Freedom", 17330, 20007),
    ("VII. 宗教 Religion（引论）",         20007, 20349),
    ("A. 自然宗教 Natural Religion",       20349, 20752),
    ("B. 艺术宗教 Art Religion",           20752, 22234),
    ("C. 天启宗教 Revealed Religion",      22234, 23497),
    ("VIII. 绝对知识 Absolute Knowing",    23497, 24834),
]


def _safe_name(title, maxlen=40):
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", title)
    return s[:maxlen]


def main():
    with open(SRC, encoding="utf-8") as f:
        lines = f.readlines()

    os.makedirs(CH_DIR, exist_ok=True)
    plan = []
    for i, (title, start, end) in enumerate(BOUNDS, 1):
        chunk = lines[start - 1 : end - 1]
        while chunk and not chunk[0].strip():
            chunk.pop(0)
        while chunk and not chunk[-1].strip():
            chunk.pop()
        text = "".join(chunk)
        fname = "{:02d}_{}.txt".format(i, _safe_name(title))
        fpath = os.path.join(CH_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(text)
        plan.append({
            "no": i,
            "title": title,
            "file": fname,
            "lines": end - start,
            "chars": len(text),
            "status": "pending",
            "published_at": None,
            "media_id": "",
        })
        print("[{:02d}] {:<34} {:>7} 字符  ->  {}".format(i, title, len(text), fname))

    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump({
            "book": "The Phenomenology of Spirit (Hegel, Baillie trans.)",
            "source": SRC,
            "chapters": len(plan),
            "updated_at": datetime.now().isoformat(),
            "pieces": plan,
        }, f, ensure_ascii=False, indent=2)
    print("\n✅ 共拆分 {} 章 -> {}".format(len(plan), CH_DIR))
    print("   计划清单 -> {}".format(PLAN))


if __name__ == "__main__":
    main()
