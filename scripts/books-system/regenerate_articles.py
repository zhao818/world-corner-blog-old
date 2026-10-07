#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量文章生成器 v2（带重试 + 断点续接）
=========================================
以「文章文件实际质量」为准判断是否需要（重新）生成，而不是信任 plan.json 的 status。
（历史问题：部分 plan.json 被错误标记为 translated，但文章文件其实是生成中断的草稿残留。）

用法:
  python regenerate_articles.py                 # 扫描全部 8 本书
  python regenerate_articles.py chuanxilu       # 只处理指定书
  python regenerate_articles.py chuanxilu sartre

特性:
  - 重试: 每次 API 调用最多 max_retries 次，指数退避，网络不稳定自动续
  - 断点续接: 已合格的文章跳过；生成成功的立即写文件+更新 plan.json，中断后重跑只处理未完成的
  - 逐篇隔离: 单篇失败不影响其他篇
"""
import os, sys, json, time, re, urllib.request
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:18001/v1/messages"
MODEL = "claude-sonnet-4-6"
AUTH = os.environ.get("ANTHROPIC_AUTH_TOKEN", "123")
BOOKS = ["schopenhauer", "aurelius", "chuanxilu", "sartre", "foucault", "body", "economics", "richdad"]

# 生成残留特征（命中即视为不合格草稿）
JUNK_PATTERNS = [
    r"We need to", r"提示词模板", r"现在，整合成", r"草拟完整内容",
    r"确保全文", r"首先，用户要求", r"作为人生哲学实践导师，基于", r"用户要求我作为",
    r"Now produce final", r"Let's draft", r"We'll give maybe",
]

def call_api(prompt, max_tokens=4096, max_retries=8):
    """调用代理，失败自动重试（指数退避 + 抖动），最多 max_retries 次"""
    body = json.dumps({
        "model": MODEL, "max_tokens": max_tokens,
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
        wait = min(2 ** attempt, 60) + (attempt * 3)  # 2,4,8,16,32,60,60,60 + 抖动
        print("  ⚠️ 第{}次失败({})，{}s后重试...".format(attempt, last_err, wait))
        time.sleep(wait)
    raise RuntimeError("调用失败(已重试{}次): {}".format(max_retries, last_err))


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

要求：语言通俗、贴近生活、有感染力。全文 1500-2500 字。直接输出最终文章，不要输出任何思考过程、计划或说明。"""


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

要求：语言通俗、贴近生活、有感染力。全文 1500-2500 字。直接输出最终文章，不要输出任何思考过程、计划或说明。

以下是本章英文原文（节选）：
=====
{sample}
====="""


def is_article_ok(path):
    """判断文章文件是否合格：有完整结构、无生成残留、行数足够"""
    if not os.path.exists(path):
        return False, "文件不存在"
    with open(path, encoding="utf-8") as f:
        c = f.read()
    lines = len(c.split("\n"))
    problems = []
    if lines < 30:
        problems.append("行数少({})".format(lines))
    if not c.strip().startswith("#"):
        problems.append("无标题")
    if "本章在讲什么" not in c:
        problems.append("缺摘要段")
    if "事上磨练" not in c:
        problems.append("缺任务段")
    if "读后思考" not in c:
        problems.append("缺思考段")
    for pat in JUNK_PATTERNS:
        if re.search(pat, c):
            problems.append("生成残留:" + pat)
            break
    return (len(problems) == 0), ("; ".join(problems) if problems else "合格")


def main():
    targets = [b for b in sys.argv[1:] if b in BOOKS] if len(sys.argv) > 1 else BOOKS
    if not targets:
        print("未知的书名，可用: " + ", ".join(BOOKS))
        return

    todo = []
    for book in targets:
        book_dir = os.path.join(SCRIPT_DIR, "books", book)
        cfg_path = os.path.join(book_dir, "book.json")
        plan_path = os.path.join(book_dir, "plan.json")
        if not os.path.exists(cfg_path) or not os.path.exists(plan_path):
            print("⏭️ {}: 缺少 book.json/plan.json，跳过".format(book))
            continue
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        with open(plan_path, encoding="utf-8") as f:
            plan_data = json.load(f)
        pieces = plan_data["pieces"]
        total = len(pieces)
        mode = cfg.get("mode", "text")
        out_dir = os.path.join(book_dir, "articles")
        os.makedirs(out_dir, exist_ok=True)

        for p in pieces:
            no = p["no"]
            fname = p.get("article_file") or "{:02d}_{}.md".format(no, re.sub(r"[^\w\u4e00-\u9fff]+", "_", p["title"])[:40])
            out_path = os.path.join(out_dir, fname)
            ok, why = is_article_ok(out_path)
            if ok:
                print("⏭️ [{}/{}] {}: 已合格，跳过".format(book, no, p["title"]))
                continue
            print("🔨 [{}/{}] {}: 需生成 ({})".format(book, no, p["title"], why))
            todo.append((book, p, cfg, plan_data, plan_path, out_path, mode, total))

    if not todo:
        print("\n✅ 全部合格，无需生成")
        return

    print("\n待生成 {} 篇，开始...".format(len(todo)))
    ok_count = 0
    fail_count = 0
    for book, p, cfg, plan_data, plan_path, out_path, mode, total in todo:
        no = p["no"]
        title = p["title"]
        print("\n[{:02d}/{:02d}] 生成中: {} ({} / {})...".format(no, total, title, book, mode))
        try:
            if mode == "knowledge":
                brief = p.get("knowledge_brief", "（本书为概念导读，无原文）")
                md = call_api(build_prompt_knowledge(cfg["title_cn"], cfg["author_cn"], title, no, total, brief))
            else:
                chapters_dir = os.path.join(SCRIPT_DIR, "books", book, "chapters")
                fpath = os.path.join(chapters_dir, p.get("file", ""))
                if not os.path.exists(fpath):
                    print("  ❌ 章节原文不存在: {}".format(fpath))
                    fail_count += 1
                    continue
                with open(fpath, encoding="utf-8") as f:
                    text = f.read()
                md = call_api(build_prompt_text(cfg["title_cn"], cfg["author_cn"], title, text, no, total))
        except Exception as e:
            print("  ❌ 生成失败: {}".format(e))
            fail_count += 1
            continue

        # 写文件（先写临时文件，再原子替换，避免半截文件）
        tmp_path = out_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(md)
        # 校验生成结果
        with open(tmp_path, encoding="utf-8") as f:
            c = f.read()
        if len(c.split("\n")) < 30 or "本章在讲什么" not in c or "事上磨练" not in c:
            print("  ❌ 生成结果不合格（结构缺失），放弃保存")
            os.remove(tmp_path)
            fail_count += 1
            continue
        os.replace(tmp_path, out_path)

        # 更新 plan.json（断点续接的关键：成功立即标记）
        p["status"] = "translated"
        p["article_file"] = os.path.basename(out_path)
        p["translated_at"] = datetime.now().isoformat()
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)
        print("  ✅ 已保存 -> {}".format(os.path.basename(out_path)))
        ok_count += 1
        time.sleep(1)

    print("\n=== 完成: 成功 {} / 失败 {} ===".format(ok_count, fail_count))
    if fail_count:
        print("重跑本命令即可续接失败项（断点续接）")


if __name__ == "__main__":
    main()
