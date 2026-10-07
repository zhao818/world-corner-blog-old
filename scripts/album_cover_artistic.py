#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""艺术感专辑封面生成器 - 更自由、更有设计感"""
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile

# 品牌色
DARK_BG = "#0D0D1A"          # 深空黑
GOLD = "#C8A03C"             # 品牌金
GOLD_LIGHT = "#E8C87C"       # 亮金
TEAL = "#00D4AA"             # 青绿点缀
CORAL = "#FF6B6B"            # 珊瑚红
WHITE = "#FFFFFF"
GRAY = "#8C8C9A"

FONT_PATH = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑

def make_album_cover(
    title: str,
    subtitle: str = "",
    category: str = "音乐专辑",
    output: str = None,
    style: str = "minimal",  # minimal | cinematic | typographic | collage
    width: int = 1080,
    height: int = 1080,
) -> str:
    """
    生成专辑封面（1:1 正方形，适配视频号/小红书/抖音封面）
    
    Styles:
    - minimal: 极简留白，大标题居中，品牌金分割线
    - cinematic: 电影感渐变背景，文字叠加，有氛围
    - typographic: 字体设计为主，文字即视觉
    - collage: 拼贴感，多层次图形叠加
    """
    
    img = Image.new("RGB", (width, height), DARK_BG)
    draw = ImageDraw.Draw(img)
    cx, cy = width // 2, height // 2
    
    # 字体加载
    def load_font(size):
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except:
            return ImageFont.load_default()
    
    if style == "minimal":
        _draw_minimal(draw, cx, cy, width, height, title, subtitle, category, load_font)
    elif style == "cinematic":
        _draw_cinematic(draw, cx, cy, width, height, title, subtitle, category, load_font, img)
    elif style == "typographic":
        _draw_typographic(draw, cx, cy, width, height, title, subtitle, category, load_font)
    elif style == "collage":
        _draw_collage(draw, cx, cy, width, height, title, subtitle, category, load_font)
    
    # 右下角品牌签名（所有风格通用）
    _draw_brand_signature(draw, width, height, load_font)
    
    if output is None:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            output = tmp.name
    img.save(output, "JPEG", quality=95)
    return output


def _draw_minimal(draw, cx, cy, w, h, title, subtitle, category, load_font):
    """极简风：大留白，居中大标题，金线分割，副标题小字"""
    f_title = load_font(72)
    f_sub = load_font(28)
    f_cat = load_font(18)
    
    # 主标题（多行自动换行）
    lines = _wrap_text(title, f_title, draw, w * 0.8)
    total_h = sum(draw.textbbox((0,0), l, font=f_title)[3] for l in lines) + (len(lines)-1)*16
    y_start = cy - total_h // 2
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=f_title)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw//2, y_start), line, fill=WHITE, font=f_title)
        y_start += bbox[3] - bbox[1] + 16
    
    # 金色分割线
    y_start += 24
    line_w = 120
    draw.line([(cx - line_w//2, y_start), (cx + line_w//2, y_start)], fill=GOLD, width=3)
    y_start += 32
    
    # 副标题
    if subtitle:
        bbox = draw.textbbox((0,0), subtitle, font=f_sub)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw//2, y_start), subtitle, fill=GRAY, font=f_sub)
        y_start += bbox[3] - bbox[1] + 20
    
    # 分类标签
    tag = f"· {category} ·"
    bbox = draw.textbbox((0,0), tag, font=f_cat)
    tw = bbox[2] - bbox[0]
    tx = cx - tw//2
    draw.rectangle([(tx-12, y_start-4), (tx+tw+12, y_start+bbox[3]-bbox[1]+4)], outline=GOLD, width=1)
    draw.text((tx, y_start), tag, fill=GOLD, font=f_cat)


def _draw_cinematic(draw, cx, cy, w, h, title, subtitle, category, load_font, img):
    """电影感：渐变背景 + 蒙版 + 文字叠加"""
    # 创建渐变背景层
    gradient = Image.new("RGB", (w, h))
    g_draw = ImageDraw.Draw(gradient)
    for y in range(h):
        ratio = y / h
        # 深空黑 -> 深蓝绿 -> 深空黑
        r = int(13 * (1-ratio) + 0 * ratio)
        g = int(13 * (1-ratio) + 40 * ratio)
        b = int(26 * (1-ratio) + 30 * ratio)
        g_draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    # 叠加到主图
    img.paste(gradient, (0, 0))
    draw = ImageDraw.Draw(img)
    
    # 添加装饰性光晕
    for _ in range(3):
        x = cx + (hash(str(_)) % 200 - 100)
        y = cy + (hash(str(_*2)) % 200 - 100)
        r = 180 + _ * 60
        overlay = Image.new("RGBA", (w, h), (0,0,0,0))
        o_draw = ImageDraw.Draw(overlay)
        o_draw.ellipse([x-r, y-r, x+r, y+r], fill=(0, 212, 170, 15))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
    
    f_title = load_font(68)
    f_sub = load_font(26)
    
    # 标题偏上
    lines = _wrap_text(title, f_title, draw, w * 0.75)
    total_h = sum(draw.textbbox((0,0), l, font=f_title)[3] for l in lines) + (len(lines)-1)*12
    y = cy - total_h // 2 - 60
    
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=f_title)
        tw = bbox[2] - bbox[0]
        # 文字阴影
        draw.text((cx - tw//2 + 2, y + 2), line, fill="#000000", font=f_title)
        draw.text((cx - tw//2, y), line, fill=WHITE, font=f_title)
        y += bbox[3] - bbox[1] + 12
    
    y += 20
    if subtitle:
        bbox = draw.textbbox((0,0), subtitle, font=f_sub)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw//2 + 1, y + 1), subtitle, fill="#000000", font=f_sub)
        draw.text((cx - tw//2, y), subtitle, fill=TEAL, font=f_sub)


def _draw_typographic(draw, cx, cy, w, h, title, subtitle, category, load_font):
    """字体设计风格：文字即视觉，大小变化、错位、重叠"""
    f_big = load_font(96)
    f_med = load_font(48)
    f_small = load_font(24)
    
    # 将标题拆字/拆词，错位排版
    words = title.replace("|", " ").split()
    if len(words) == 1:
        words = list(title)  # 单字拆分
    
    y = cy - 100
    x_offsets = [-60, -20, 20, 60, -40, 0, 40]
    
    for i, word in enumerate(words):
        font = f_big if i < 2 else f_med
        color = GOLD if i % 2 == 0 else WHITE
        x_off = x_offsets[i % len(x_offsets)]
        
        bbox = draw.textbbox((0,0), word, font=font)
        tw = bbox[2] - bbox[0]
        x = cx - tw//2 + x_off
        
        # 重叠阴影效果
        draw.text((x+3, y+3), word, fill="#0D0D1A", font=font)
        draw.text((x, y), word, fill=color, font=font)
        y += (bbox[3] - bbox[1]) + 8
    
    if subtitle:
        y += 30
        bbox = draw.textbbox((0,0), subtitle, font=f_small)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw//2, y), subtitle, fill=TEAL, font=f_small)


def _draw_collage(draw, cx, cy, w, h, title, subtitle, category, load_font):
    """拼贴风：几何色块 + 文字穿插"""
    # 背景几何色块
    blocks = [
        (0.1, 0.15, 0.35, 0.7, TEAL + "33"),
        (0.6, 0.2, 0.35, 0.6, CORAL + "22"),
        (0.25, 0.65, 0.5, 0.25, GOLD + "1A"),
    ]
    for bx, by, bw, bh, color in blocks:
        x1, y1 = int(w*bx), int(h*by)
        x2, y2 = int(w*(bx+bw)), int(h*(by+bh))
        draw.rounded_rectangle([x1, y1, x2, y2], radius=24, fill=color, outline=GOLD + "44", width=1)
    
    # 标题覆盖在色块上
    f_title = load_font(64)
    f_sub = load_font(24)
    
    lines = _wrap_text(title, f_title, draw, w * 0.6)
    y = cy - 80
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=f_title)
        tw = bbox[2] - bbox[0]
        # 白描边
        for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
            draw.text((cx - tw//2 + dx, y + dy), line, fill=DARK_BG, font=f_title)
        draw.text((cx - tw//2, y), line, fill=WHITE, font=f_title)
        y += bbox[3] - bbox[1] + 14
    
    if subtitle:
        y += 10
        bbox = draw.textbbox((0,0), subtitle, font=f_sub)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw//2, y), subtitle, fill=GOLD_LIGHT, font=f_sub)


def _draw_brand_signature(draw, w, h, load_font):
    """右下角品牌签名"""
    f_sig = load_font(14)
    brand = "世界一隅 · WORLD CORNER"
    date = "2026.07.13"
    
    # 签名行
    bbox = draw.textbbox((0,0), brand, font=f_sig)
    tw = bbox[2] - bbox[0]
    x = w - tw - 30
    y = h - 50
    draw.text((x, y), brand, fill=GOLD, font=f_sig)
    
    # 日期
    f_date = load_font(11)
    bbox = draw.textbbox((0,0), date, font=f_date)
    tw = bbox[2] - bbox[0]
    draw.text((w - tw - 30, y + 20), date, fill=GRAY, font=f_date)
    
    # 三个金点
    for i in range(3):
        px = x - 18 - i * 16
        draw.ellipse([(px, y+6), (px+8, y+14)], fill=GOLD)


def _wrap_text(text, font, draw, max_width):
    """简单换行：按字符拆分"""
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = draw.textbbox((0,0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines if lines else [text]


if __name__ == "__main__":
    # 测试四种风格
    title = "环球旅行日志"
    subtitle = "这一周不必太匆忙 跟着心跳去流浪"
    category = "音乐专辑"
    
    desktop = os.path.expanduser("~/Desktop")
    
    for style in ["minimal", "cinematic", "typographic", "collage"]:
        out = os.path.join(desktop, f"album_cover_{style}.jpg")
        make_album_cover(title, subtitle, category, out, style=style)
        print(f"✅ {style}: {out}")