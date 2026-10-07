# -*- coding: utf-8 -*-
"""《文明的阶梯》7 篇连载文章 → 成书 markdown

读 content/posts/civilization-ladder/*.md,剥 frontmatter,
机械改写连载衔接语("下一篇见"等)为书内措辞,组装为
# 序言 + # 第一篇..第五篇 + # 跋 结构,输出 books-system/文明的阶梯-灵魂之觅版.md。

用法:python merge_civilization.py
"""
import os
import re

SRC_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "..", "content", "posts", "civilization-ladder"))
BASE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(BASE, "文明的阶梯-灵魂之觅版.md")

# 文件名 → 章标题(阅读器 flat 模式按 # 一级切章)
CHAPTERS = [
    ("00-intro.md", "# 序言 我们为什么要爬一座看不见的阶梯"),
    ("01-feed-the-first-step.md", "# 第一篇 喂饱,文明的第一级阶梯"),
    ("02-hungry-beyond-the-body.md", "# 第二篇 人不止一层饿"),
    ("03-happiness-is-upgrade.md", "# 第三篇 幸福就是升级"),
    ("04-lighthouse.md", "# 第四篇 灯塔,我们唯一能做的事"),
    ("05-daily-practice.md", "# 第五篇 每日必修与总纲"),
    ("06-epilogue.md", "# 跋 一群人亮起来"),
]

# 连载衔接语 → 书内措辞(按顺序替换)
BODY_FIX = [
    ("因为它正是我们下一篇文章要打开的那扇门。", "它正是下一章要打开的那扇门。"),
    ("我们下一篇,就讲那个地方。", "下一章,我们就讲那个地方。"),
    ("下一篇文章,我们要回答一个更关键的问题", "下一章,我们要回答一个更关键的问题"),
    ("我们下一篇见。", ""),
    ("先留一个念头给你,我们下一篇接上。", "先留一个念头给你,下一章接上。"),
    ("下一篇,我们要面对一个让人不太舒服的问题", "下一章,我们要面对一个让人不太舒服的问题"),
    ("上一篇文章,我们立下了全书的地基", "上一章,我们立下了全书的地基"),
    ("上一篇文章,我们说:人饿着", "上一章,我们说:人饿着"),
    ("上一篇,我们立下了全书最重要的一个判断", "上一章,我们立下了全书最重要的一个判断"),
]


def strip_frontmatter(text):
    """去掉 --- frontmatter ---,返回正文"""
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, flags=re.S)
    if m:
        return text[m.end():]
    return text


def main():
    missing = [f for f, _ in CHAPTERS if not os.path.exists(os.path.join(SRC_DIR, f))]
    if missing:
        print("缺失源文件:", missing)
        return

    out = []
    for fname, title in CHAPTERS:
        text = open(os.path.join(SRC_DIR, fname), encoding="utf-8").read()
        body = strip_frontmatter(text).strip()
        for a, b in BODY_FIX:
            body = body.replace(a, b)
        # 清掉可能残留的空行堆叠
        body = re.sub(r"\n{3,}", "\n\n", body)
        out.append(title + "\n\n" + body)

    text = "\n\n---\n\n".join(out) + "\n"
    open(DST, "w", encoding="utf-8").write(text)

    # 校验残留连载语
    leftovers = []
    for w in ("下一篇", "上一篇文章", "上一篇"):
        if w in text:
            leftovers.append("残留「%s」" % w)
    print("输出:", DST)
    print("总字数(含标题):", len(text))
    print("章数:", len(CHAPTERS))
    if leftovers:
        print("⚠️ 需人工检查:", leftovers)
    else:
        print("✅ 无连载语残留")


if __name__ == "__main__":
    main()
