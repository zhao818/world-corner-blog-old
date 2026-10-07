#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建合集发布队列到 54 项（身心社财完整版），回填已发布痕迹"""
import os, json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 正文顺序（九阶段）
BOOK_ORDER = ['schopenhauer', 'aurelius', 'chuanxilu', 'sartre', 'foucault',
              'body', 'economics', 'richdad']
TITLES = json.load(open(os.path.join(SCRIPT_DIR, 'collection_titles.json'), encoding='utf-8'))['titles']

pieces = []
# seq 0: 开篇引言
pieces.append({"seq": 0, "type": "collection", "title": "开篇引言：这套合集要做什么",
               "source": "books/_collection/00_开篇引言.md", "status": "pending", "published_at": None, "media_id": ""})

# seq 1-52: 正文
seq = 1
for book in BOOK_ORDER:
    plan_path = os.path.join(SCRIPT_DIR, 'books', book, 'plan.json')
    with open(plan_path, encoding='utf-8') as f:
        d = json.load(f)
    for p in d['pieces']:
        pieces.append({
            "seq": seq, "type": "article", "book": book, "no": p['no'],
            "title": TITLES.get(book, {}).get(str(p['no']), p['title']),
            "source": os.path.join('books', book, 'articles', p.get('article_file', '')),
            "status": p.get('status', 'pending'),
            "published_at": p.get('published_at'),
            "media_id": p.get('media_id', ''),
        })
        seq += 1

# seq 53: 完结篇
pieces.append({"seq": 53, "type": "collection", "title": "完结篇：五阶段收官",
               "source": "books/_collection/35_完结篇.md", "status": "pending", "published_at": None, "media_id": ""})

plan = {"collection": "内心的修炼", "total": len(pieces),
        "updated_at": datetime.now().isoformat(), "pieces": pieces}
with open(os.path.join(SCRIPT_DIR, 'collection_plan.json'), 'w', encoding='utf-8') as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

# 回填已发布痕迹（开篇引言 + 叔本华1）
# 从 archive info 找历史记录
for p in pieces:
    if p['seq'] == 0:
        p['status'] = 'published'
        p['published_at'] = '2026-08-04T20:46:55'
        p['media_id'] = 'uohiBa_iOzkD2OcZecjBQIpghsnGZvwVjr3kIEyC02RSF11UTjSWYp6QPhmfV_Kb'
    if p['seq'] == 1:
        p['status'] = 'published'
        p['published_at'] = '2026-08-04T19:47:58'
        p['media_id'] = 'uohiBa_iOzkD2OcZecjBQCsVZrrKb8pKi4bVrUzHlQONKbtrxFllC9rchThF8085'
with open(os.path.join(SCRIPT_DIR, 'collection_plan.json'), 'w', encoding='utf-8') as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)

print("✅ 发布队列已重建: {} 项".format(len(pieces)))
published = [p['seq'] for p in pieces if p.get('status') == 'published']
print("   已发布: {}".format(published))
np_ = next((p for p in pieces if p.get('status') != 'published'), None)
print("   下一篇: [{}] 「{}」".format(np_['seq'], np_['title']) if np_ else "全部完成")
