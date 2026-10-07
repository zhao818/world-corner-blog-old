#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用导读翻译器 v3（五维系统版）：调 18001 代理生成中文导读 Markdown
支持两种模式:
  mode=text      : 基于原文拆章翻译（叔本华/奥勒留）
  mode=knowledge : AI 知识导读，无原文（传习录/萨特/福柯）
新增: ✦事上磨练 任务（每篇带本周真实行动任务+反思模板）
用法:
  python translate_guide.py schopenhauer 1      # 原文模式
  python translate_guide.py chuanxilu 1         # 知识导读模式
  python translate_guide.py schopenhauer --all  # 全部
"""
import os, sys, json, time, re
from datetime import datetime
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:18001/v1/messages"
MODEL = "claude-sonnet-4-6"
AUTH = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")


def call_api(prompt, max_tokens=4096, max_retries=5):
    """调用代理，失败自动重试（指数退避），最多 max_retries 次"""
    import time as _t
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(API, data=body, headers={
                "Content-Type": "application/json",
                "x-api-key": AUTH,
                "anthropic-version": "2023-06-01",
            })
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            parts = data.get("content", [])
            text = "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
            if text:
                return text
            last_err = "空响应"
        except Exception as e:
            last_err = str(e)
        wait = min(2 ** attempt, 60)  # 2,4,8,16,32 -> 封顶60s
        print("  ⚠️ 第{}次失败({})，{}s后重试...".format(attempt, last_err, wait))
        _t.sleep(wait)
    raise RuntimeError("调用失败(已重试{}次): {}".format(max_retries, last_err))


def build_prompt_text(book_cn, author_cn, title, chapter_text, no, total):
    if len(chapter_text) > 24000:
        head = chapter_text[:12000]
        mid = chapter_text[len(chapter_text)//2 - 3000: len(chapter_text)//2 + 3000]
        tail = chapter_text[-6000:]
        sample = head + "\n\n[...中段略...]\n\n" + mid + "\n\n[...结尾...]\n\n" + tail
    else:
        sample = chapter_text
    return f"""你是人生哲学实践导师。任务是把{author_cn}《{book_cn}》的「{title}」这一章，写成一篇能指导读者实际生活的中文导读文章（第{no}/{total}篇）。

请严格按以下结构输出（用 Markdown）：

# 《{book_cn}》| {title}

## 本章在讲什么（300字以内）
用大白话概括这一章的核心主题，讲清楚它对我们普通人生活的意义。

## 核心观点解读（3-5 条）
每条：小标题 + 200-300 字解读。用现代生活案例解释核心概念，避免学术黑话。

## 原文精译（选 2-3 段最有代表性的段落）
每段：英文原文引用（不超过 120 词）+ 中文翻译 + 一句解读。

## ✦ 事上磨练（本周任务）
这是本系列的核心：设计 1 个本周真实可做的具体行动任务（不是抽象感悟）。
要求：
- 必须是这周就能完成的具体事，小到"对一个人说一句真话"也行
- 与本章核心观点强相关
- 给 3 行反思记录模板：①做了什么 ②卡在哪 ③下次怎么改

## 读后思考（2 个问题）
引导读者联系自身现实思考。

要求：语言通俗、贴近生活、有感染力。全文 1500-2500 字。

以下是本章英文原文（节选）：
=====
{sample}
====="""


def build_prompt_knowledge(book_cn, author_cn, title, no, total, brief):
    return f"""你是人生哲学实践导师。任务是基于{author_cn}《{book_cn}》的核心思想（注意：本书无逐字原文，用你的知识储备），围绕「{title}」这一主题，写一篇能指导读者实际生活的中文导读文章（第{no}/{total}篇）。

主题参考：{brief}

请严格按以下结构输出（用 Markdown）：

# 《{book_cn}》| {title}

## 本章在讲什么（300字以内）
用大白话概括这一主题的核心思想，讲清楚它对普通人生活的意义。

## 核心观点解读（3-5 条）
每条：小标题 + 200-300 字解读。用现代生活案例解释核心概念，避免学术黑话。

## 思想精要（2-3 个关键概念）
每个概念：概念解释 + 与本书整体思想的关系 + 一个现实应用例子。

## ✦ 事上磨练（本周任务）
这是本系列的核心：设计 1 个本周真实可做的具体行动任务（不是抽象感悟）。
要求：
- 必须是这周就能完成的具体事，小到"对一个人说一句真话"也行
- 与本章核心观点强相关
- 给 3 行反思记录模板：①做了什么 ②卡在哪 ③下次怎么改

## 读后思考（2 个问题）
引导读者联系自身现实思考。

要求：语言通俗、贴近生活、有感染力。全文 1500-2500 字。"""


def main():
    argv = sys.argv[1:]
    if len(argv) < 2:
        print("用法: python translate_guide.py <book> <章号|--all>")
        return
    book_name, rest = argv[0], argv[1]
    book_dir = os.path.join(SCRIPT_DIR, "books", book_name)
    cfg_path = os.path.join(book_dir, "book.json")
    plan_path = os.path.join(book_dir, "plan.json")
    if not os.path.exists(plan_path):
        print("❌ 未找到 plan.json，先运行: python split_book.py {}".format(book_name))
        return
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    with open(plan_path, encoding="utf-8") as f:
        plan_data = json.load(f)
    pieces = plan_data["pieces"]
    total = len(pieces)
    mode = cfg.get("mode", "text")

    if rest == "--all":
        # 断点续跑：跳过已翻译的
        targets = [p["no"] for p in pieces if p.get("status") != "translated"]
        skipped = [p["no"] for p in pieces if p.get("status") == "translated"]
        if skipped:
            print("⏭️ 跳过已翻译: {}".format(skipped))
        if not targets:
            print("✅ 全部已翻译，无需重跑")
            return
    else:
        targets = [int(rest)]

    out_dir = os.path.join(book_dir, "articles")
    os.makedirs(out_dir, exist_ok=True)

    for no in targets:
        p = next((x for x in pieces if x["no"] == no), None)
        if not p:
            print("章号 {} 不存在".format(no))
            continue
        print("[{:02d}/{:02d}] 翻译中: {} (模式:{})...".format(no, total, p["title"], mode))
        try:
            if mode == "knowledge":
                brief = p.get("knowledge_brief", "（本书为概念导读，无原文）")
                md = call_api(build_prompt_knowledge(cfg["title_cn"], cfg["author_cn"], p["title"], no, total, brief))
            else:
                fpath = os.path.join(book_dir, "chapters", p["file"])
                with open(fpath, encoding="utf-8") as f:
                    text = f.read()
                md = call_api(build_prompt_text(cfg["title_cn"], cfg["author_cn"], p["title"], text, no, total))
        except Exception as e:
            print("  ❌ 翻译失败: {}".format(e))
            continue
        out_name = "{:02d}_{}.md".format(no, re.sub(r"[^\w\u4e00-\u9fff]+", "_", p["title"])[:40])
        out_path = os.path.join(out_dir, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        p["status"] = "translated"
        p["article_file"] = out_name
        p["translated_at"] = datetime.now().isoformat()
        print("  ✅ 已保存 -> {}".format(out_name))
        time.sleep(1)

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_data, f, ensure_ascii=False, indent=2)
    done = sum(1 for x in pieces if x["status"] == "translated")
    print("\n进度: {}/{} 章已翻译".format(done, total))


if __name__ == "__main__":
    main()

