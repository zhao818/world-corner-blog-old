#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成合集发布队列 collection_plan.json（36项：00开篇 + 34正文 + 35完结）
从各书 plan.json 回填已发布痕迹
"""
import os, json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 正文顺序：按合集大纲的阶段顺序
BOOK_ORDER = ['schopenhauer', 'aurelius', 'chuanxilu', 'sartre', 'foucault']
TITLES = json.load(open(os.path.join(SCRIPT_DIR, 'collection_titles.json'), encoding='utf-8'))['titles']

pieces = []

# seq 0: 开篇引言
pieces.append({
    "seq": 0, "type": "collection", "title": "开篇引言：这套合集要做什么",
    "source": "books/_collection/00_开篇引言.md",
    "status": "pending", "published_at": None, "media_id": "",
})

# seq 1-34: 正文
seq = 1
for book in BOOK_ORDER:
    plan_path = os.path.join(SCRIPT_DIR, 'books', book, 'plan.json')
    with open(plan_path, encoding='utf-8') as f:
        d = json.load(f)
    for p in d['pieces']:
        pieces.append({
            "seq": seq, "type": "article",
            "book": book, "no": p['no'],
            "title": TITLES.get(book, {}).get(str(p['no']), p['title']),
            "source": os.path.join('books', book, 'articles', p.get('article_file', '')),
            "status": p.get('status', 'pending'),
            "published_at": p.get('published_at'),
            "media_id": p.get('media_id', ''),
        })
        seq += 1

# seq 35: 完结篇
pieces.append({
    "seq": 35, "type": "collection", "title": "完结篇：五阶段收官",
    "source": "books/_collection/35_完结篇.md",
    "status": "pending", "published_at": None, "media_id": "",
})

plan = {
    "collection": "内心的修炼",
    "total": len(pieces),
    "updated_at": datetime.now().isoformat(),
    "pieces": pieces,
}
with open(os.path.join(SCRIPT_DIR, 'collection_plan.json'), 'w', encoding='utf-8') as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

print("合集发布队列已生成: {} 项".format(len(pieces)))
for p in pieces:
    st = "✅已发" if p.get('status') == 'published' else "⬜待发"
    print("[{:02d}] {} {} 「{}」".format(p['seq'], st, p.get('book','合集') if p.get('type')=='article' else '合集', p['title']))
