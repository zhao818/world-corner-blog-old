# -*- coding: utf-8 -*-
"""《内心的修炼》md → epub 生成器

打磨书稿后重新生成 epub 用：
    python build_epub.py
输出：books-system/内心的修炼-v4-灵魂之觅版.epub
"""
import os
import re
import zipfile

from markdown import markdown
from ebooklib import epub

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "内心的修炼-v4-灵魂之觅版.md")
DST = os.path.join(BASE, "内心的修炼-v4-灵魂之觅版.epub")

CSS = """
body { font-family: "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; line-height: 1.85; }
h1 { text-align: center; margin-top: 2em; }
h2 { border-left: 4px solid #7c3aed; padding-left: .5em; margin-top: 1.6em; }
h3, h4 { color: #374151; }
blockquote { border-left: 3px solid #7c3aed; margin: 1em 0; padding: .4em 1em; color: #4b5563; background: #f7f5ff; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
td, th { border: 1px solid #e5e7eb; padding: 6px 10px; font-size: .92em; }
hr { border: none; border-top: 1px dashed #cbd5e1; margin: 1.5em 0; }
"""


def split_chapters(text):
    """按 # 与 ## 标题行切分,返回 [(level, title, body), ...]"""
    chapters = []
    cur_lines = []
    cur_level = 0
    cur_title = ""

    def flush():
        nonlocal cur_lines
        if cur_lines:
            body = "\n".join(cur_lines).strip()
            # 去掉正文开头紧跟的标题行(标题单独存)
            body = re.sub(r"^#{1,6}\s+.*$", "", body, count=1, flags=re.M).strip()
            chapters.append((cur_level, cur_title, body))
            cur_lines = []

    for ln in text.splitlines():
        m = re.match(r"^(#{1,2})\s+(.+)$", ln)
        if m:
            flush()
            cur_level = len(m.group(1))
            cur_title = m.group(2).strip()
        else:
            cur_lines.append(ln)
    flush()
    return chapters


def get_cover_bytes():
    """优先从现有 epub 里抽封面,没有则跳过封面"""
    if os.path.exists(DST):
        try:
            with zipfile.ZipFile(DST) as z:
                for n in z.namelist():
                    if n.lower().endswith((".jpg", ".jpeg", ".png")) and "cover" in n.lower():
                        return z.read(n)
        except Exception as e:
            print("提取旧封面失败:", e)
    return None


def main():
    text = open(SRC, encoding="utf-8").read()
    chapters = split_chapters(text)
    print("章节数:", len(chapters))

    book = epub.EpubBook()
    book.set_identifier("neixin-xiulian-v4-2026")
    book.set_title("内心的修炼")
    book.set_language("zh")
    book.add_author("美好需要创造")

    # 样式
    style = epub.EpubItem(uid="style", file_name="style/stylesheet.css", media_type="text/css", content=CSS)
    book.add_item(style)

    # 封面(从旧 epub 抽取复用)
    cover = get_cover_bytes()
    if cover:
        book.set_cover("cover.jpg", cover)

    # 章节文件
    epub_chapters = []
    for i, (level, title, body) in enumerate(chapters):
        html_body = markdown(body, extensions=["tables", "sane_lists"])
        content = '<h%d class="chapter-title">%s</h%d>\n%s' % (level, title, level, html_body)
        ch = epub.EpubHtml(
            title=title,
            file_name="index_split_%03d.xhtml" % i,
            lang="zh",
            content=content,
        )
        ch.add_item(style)
        book.add_item(ch)
        epub_chapters.append((level, ch))

    # 目录:## 章节嵌套在其所属的 # 篇章之下
    # ebooklib 嵌套格式:(父章节链接, [子章节, ...])
    toc = []
    current = None
    for level, ch in epub_chapters:
        if level == 1:
            current = []
            toc.append((ch, current))
        else:
            if current is not None:
                current.append(ch)
            else:
                toc.append(ch)
    book.toc = toc

    # 书脊按阅读顺序全部排入
    book.spine = ["nav"] + [ch for _, ch in epub_chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 延伸阅读:读完这本(方法)→ 引导看总纲方向(闭环)
    ext_content = """<h2>延伸阅读</h2>
<p><strong>学会了方法,接下来往哪走?</strong></p>
<p>《内心的修炼》把可上手的方法递到了你手上。但你可能还在问:我们到底要往哪儿去?</p>
<blockquote>《文明的阶梯》 · 总纲。文明的每一次跃迁,都是一场「喂饱」的革命——先喂饱身体,再喂饱思想;而一群人亮起来,才是文明真正站上的那一级阶梯。</blockquote>
<p><strong>三本书 · 阅读顺序</strong></p>
<ul>
<li>《幸福的内在》 ✓ 已读 · 看到问题</li>
<li>《内心的修炼》 ✓ 已读 · 学会方法</li>
<li>《文明的阶梯》 → 接下来 · 看清方向</li>
</ul>
<p><strong>在线阅读</strong> · 世界一隅:worldcorner.xyz/read/civilization/</p>"""
    ext_ch = epub.EpubHtml(title="延伸阅读", file_name="index_extension.xhtml", lang="zh", content=ext_content)
    ext_ch.add_item(style)
    book.add_item(ext_ch)
    book.toc.append(ext_ch)
    book.spine.append(ext_ch)

    epub.write_epub(DST, book)
    size = os.path.getsize(DST)
    print("已生成:", DST)
    print("大小: %.1f KB" % (size / 1024))


if __name__ == "__main__":
    main()
