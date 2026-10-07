#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导读式翻译脚本：调用本地 18001 代理 (DeepSeek V4)，把章节英文原文转成中文导读 Markdown
用法:
  python translate_guide.py 1        # 翻译第 1 章
  python translate_guide.py 1 2 3    # 翻译多章
  python translate_guide.py --all    # 翻译全部（逐章，慢）
输出: articles/01_*.md ...  并更新 plan.json 的 status=translated
"""
import os, sys, json, time, re
from datetime import datetime
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CH_DIR = os.path.join(SCRIPT_DIR, "chapters")
OUT_DIR = os.path.join(SCRIPT_DIR, "articles")
PLAN = os.path.join(SCRIPT_DIR, "plan.json")

API = "http://127.0.0.1:18001/v1/messages"
MODEL = "claude-sonnet-4-6"  # 本地代理映射到 DeepSeek V4 Flash
AUTH = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

# 章节对应的中文标题（用于 Markdown 标题）
CN_TITLES = {
    1: "导论：论科学认识",
    2: "第一章 意识",
    3: "第二章 自我意识",
    4: "理性（引论）",
    5: "观察的理性",
    6: "理性的现实化",
    7: "自在而自为的个体性",
    8: "精神（引论）",
    9: "真实的精神：伦理秩序",
    10: "自我异化的精神：教化",
    11: "异化精神的世界",
    12: "启蒙",
    13: "绝对自由与恐怖",
    14: "宗教（引论）",
    15: "自然宗教",
    16: "艺术宗教",
    17: "天启宗教",
    18: "绝对知识",
}


def call_api(prompt, max_tokens=4096):
    """调用本地 18001 代理，返回文本"""
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json",
        "x-api-key": AUTH,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = data.get("content", [])
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()


def build_prompt(title, chapter_text):
    """构造导读式翻译提示词：输出 章首小结 + 核心段落翻译 + 白话解读"""
    # 章节文本较长，截取合理长度（token 限制内），保留开头+中段+结尾
    if len(chapter_text) > 24000:
        head = chapter_text[:12000]
        mid = chapter_text[len(chapter_text)//2 - 3000: len(chapter_text)//2 + 3000]
        tail = chapter_text[-6000:]
        sample = head + "\n\n[...中段略...]\n\n" + mid + "\n\n[...结尾...]\n\n" + tail
    else:
        sample = chapter_text
    return f"""你是哲学普及作家，任务是把黑格尔《精神现象学》的「{title}」这一章，写成一篇中文导读文章，让普通读者能读懂。

请严格按以下结构输出（用 Markdown）：

# {title}

## 本章在讲什么（300字以内）
用大白话概括这一章的核心主题和论证主线。

## 核心观点解读（3-5 条）
每条：小标题 + 200-300 字解读。解释黑格尔的关键概念（如自在/自为、扬弃、绝对精神、主奴辩证法等，若出现），用生活化例子说明。

## 原文精译（选 3 段最有代表性的段落）
每段：英文原文引用（不超过 150 词）+ 中文翻译 + 一句解读。

## 本章金句（2-3 句）
从原文挑选最精辟的句子，中英对照。

## 读后思考（2 个问题）
引导读者联系现实思考的问题。

要求：语言通俗易懂，避免学术黑话堆砌；专业术语首次出现时给白话解释。全文 1500-2500 字。

以下是本章英文原文（节选）：
=====
{sample}
====="""


def main():
    with open(PLAN, encoding="utf-8") as f:
        plan_data = json.load(f)
    pieces = plan_data["pieces"]

    argv = sys.argv[1:]
    if "--all" in argv:
        targets = [p["no"] for p in pieces]
    else:
        targets = [int(a) for a in argv if a.isdigit()]
    if not targets:
        print("用法: python translate_guide.py <章号> [章号...] 或 --all")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    for no in targets:
        p = next((x for x in pieces if x["no"] == no), None)
        if not p:
            print(f"章号 {no} 不存在")
            continue
        fpath = os.path.join(CH_DIR, p["file"])
        with open(fpath, encoding="utf-8") as f:
            text = f.read()
        cn = CN_TITLES.get(no, p["title"])
        print(f"[{no:02d}] 翻译中: {cn} ({len(text)} 字符)...")
        try:
            md = call_api(build_prompt(cn, text))
        except Exception as e:
            print(f"  ❌ 翻译失败: {e}")
            continue
        out_name = "{:02d}_{}.md".format(no, re.sub(r"[^\w\u4e00-\u9fff]+", "_", cn)[:40])
        out_path = os.path.join(OUT_DIR, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        p["status"] = "translated"
        p["article_file"] = out_name
        p["translated_at"] = datetime.now().isoformat()
        print(f"  ✅ 已保存 -> {out_name}")
        time.sleep(1)  # 避免过快请求

    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, ensure_ascii=False, indent=2)
    done = sum(1 for x in pieces if x["status"] == "translated")
    print(f"\n进度: {done}/{len(pieces)} 章已翻译")


if __name__ == "__main__":
    main()
