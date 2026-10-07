#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用拆书器（v2 泛化版）：把任意英文书按章节边界切成章节文件
用法:
  python split_book.py schopenhauer        # 用 books/schopenhauer/book.json 配置
  python split_book.py aurelius
  python split_book.py --list              # 列出所有可用书
配置: books/<name>/book.json
  {
    "name": "schopenhauer",
    "title_cn": "人生的智慧",
    "author_cn": "叔本华",
    "source": "C:/Users/zhaot/Downloads/Hegel/Schopenhauer_Wisdom_of_Life_10741.txt",
    "bounds": [["第一章标题", 起始行, 结束行], ...],
    "cn_titles": {"1": "中文标题", ...}
  }
"""
import os, sys, json, re, argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(SCRIPT_DIR, "books")


def safe_name(s, maxlen=40):
    return re.sub(r"[^\w\u4e00-\u9fff]+", "_", s)[:maxlen]


def split_book(book_name):
    cfg_path = os.path.join(BOOKS_DIR, book_name, "book.json")
    if not os.path.exists(cfg_path):
        print("❌ 未找到配置: {}".format(cfg_path))
        return None
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    src = cfg["source"]
    if not os.path.exists(src):
        print("❌ 源文件不存在: {}".format(src))
        return None
    with open(src, encoding="utf-8") as f:
        lines = f.readlines()

    ch_dir = os.path.join(BOOKS_DIR, book_name, "chapters")
    os.makedirs(ch_dir, exist_ok=True)
    plan = []
    bounds = cfg["bounds"]
    for i, (title, start, end) in enumerate(bounds, 1):
        chunk = lines[start - 1 : end - 1]
        while chunk and not chunk[0].strip():
            chunk.pop(0)
        while chunk and not chunk[-1].strip():
            chunk.pop()
        text = "".join(chunk)
        fname = "{:02d}_{}.txt".format(i, safe_name(title))
        with open(os.path.join(ch_dir, fname), "w", encoding="utf-8") as f:
            f.write(text)
        cn = cfg.get("cn_titles", {}).get(str(i), title)
        plan.append({
            "no": i,
            "title": cn,
            "file": fname,
            "lines": end - start,
            "chars": len(text),
            "status": "pending",
            "published_at": None,
            "media_id": "",
        })
        print("[{:02d}] {:<30} {:>7} 字符".format(i, cn, len(text)))

    plan_path = os.path.join(BOOKS_DIR, book_name, "plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump({
            "book": cfg["title_cn"],
            "author": cfg["author_cn"],
            "source": src,
            "chapters": len(plan),
            "updated_at": datetime.now().isoformat(),
            "pieces": plan,
        }, f, ensure_ascii=False, indent=2)
    print("\n✅ {} 拆成 {} 章 -> {}".format(cfg["title_cn"], len(plan), ch_dir))
    return plan_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("book", nargs="?", help="书名（books/ 下的目录名）")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for b in sorted(os.listdir(BOOKS_DIR)):
            if os.path.isdir(os.path.join(BOOKS_DIR, b)):
                print(" ", b)
    elif args.book:
        split_book(args.book)
    else:
        ap.print_help()
