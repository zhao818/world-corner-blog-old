#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成默认封面: 900x383 深色底 + 金色标题"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover_default.jpg")
W, H = 900, 383
img = Image.new("RGB", (W, H), (24, 26, 38))
d = ImageDraw.Draw(img)

# 背景渐变（顶部浅、底部深）
for y in range(H):
    t = y / H
    c = (int(24 + 30*t), int(26 + 34*t), int(38 + 48*t))
    d.line([(0, y), (W, y)], fill=c)

# 装饰线
d.rectangle([60, H-70, 840, H-66], fill=(212, 175, 55))
d.rectangle([60, 52, 66, H-70], fill=(212, 175, 55))

# 主标题
font_main = None
for fp in ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"]:
    try:
        font_main = ImageFont.truetype(fp, 56)
        break
    except Exception:
        continue
font_sub = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24) if os.path.exists("C:/Windows/Fonts/msyh.ttc") else None

d.text((120, 120), "黑格尔《精神现象学》", font=font_main, fill=(240, 240, 245))
if font_sub:
    d.text((120, 220), "导读系列 · 边读边学边发", font=font_sub, fill=(212, 175, 55))

img.save(OUT, "JPEG", quality=92)
print("封面已生成:", OUT, os.path.getsize(OUT), "bytes")
