#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取微信公众号草稿箱最新草稿，提取吸引人标题，生成品牌风格封面
用法:
  python fetch_wechat_drafts.py --list          # 列出草稿
  python fetch_wechat_drafts.py --cover         # 为最新草稿生成封面
  python fetch_wechat_drafts.py                 # 默认列出并生成封面
"""

import os
import sys
import json
import requests
import argparse
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# 添加路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, "platforms"))

from platforms.base import (
    DARK_BG, GOLD, BRAND,
    get_platform_cookies, update_platform_cookies,
)

FONT_PATH = "C:/Windows/Fonts/msyh.ttc"


def get_access_token():
    """获取微信 access_token"""
    creds = get_platform_cookies("wechat")
    appsecret = creds.get("appsecret", "")
    if not appsecret:
        env_file = os.path.expanduser("~/.env_wx")
        if os.path.exists(env_file):
            for line in open(env_file, encoding="utf-8"):
                line = line.strip()
                if line.startswith("WX_APPSECRET="):
                    appsecret = line.split("=", 1)[1].strip()
                    break
    
    if not appsecret:
        return None
    
    r = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={
            "grant_type": "client_credential",
            "appid": "wx331b651c8159fdcb",
            "secret": appsecret
        },
        timeout=15
    )
    data = r.json()
    token = data.get("access_token")
    if token:
        update_platform_cookies("wechat", {"access_token": token})
    return token


def list_drafts(token):
    """获取草稿列表 - 使用 batchget 接口"""
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/batchget",
        params={"access_token": token},
        json={"offset": 0, "count": 20, "no_content": 1},
        timeout=15
    )
    r.encoding = 'utf-8'
    return r.json()


def get_draft(token, media_id):
    """获取草稿详情"""
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/get",
        params={"access_token": token},
        json={"media_id": media_id},
        timeout=15
    )
    r.encoding = 'utf-8'
    return r.json()


def extract_appealing_title(title, digest):
    """从原标题和摘要中提取/生成吸引人的标题（<=9字）"""
    import re
    
    # 清理标题：保留中文、英文、数字、常用标点
    title_clean = title.replace("：", ":").replace("，", ",").replace("。", ".")
    digest_clean = digest.replace("：", ":").replace("，", ",").replace("。", ".")
    
    # 常见的吸引人关键词（按优先级排序）
    hooks = [
        "避坑", "实测", "亲测", "揭秘", "真相", "内幕", "技巧", "方法",
        "指南", "教程", "从0到1", "小白", "高手", "效率", "提效", "倍增",
        "省时", "省力", "自动化", "AI", "ChatGPT", "DeepSeek", "提示词",
        "变现", "副业", "赚钱", "收入", "自由", "财富", "认知", "思维",
        "底层逻辑", "核心", "本质", "一针见血", "醍醐灌顶", "拍案叫绝",
        "Agent", "工作流", "开源", "方案", "进化", "实战", "落地", "深度解析"
    ]
    
    # 结合标题和摘要查找关键词
    combined = title_clean + " " + digest_clean
    found_hooks = [h for h in hooks if h in combined]
    
    if found_hooks:
        # 优先用找到的钩子词
        hook = found_hooks[0]
        # 尝试组合成 <=9字的标题
        if len(hook) <= 5:
            # 从标题提取关键名词（2-4字的中文词）
            title_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', title_clean)
            # 过滤掉钩子词本身和通用词
            filter_words = {"这个", "那个", "那些", "这些", "什么", "怎么", "为什么", 
                          "就是", "不是", "可以", "没有", "一个", "两个", "三个",
                          "进化", "工作流", "开源", "方案", "项目", "代码"}
            candidates = [w for w in title_words if w not in hook and w not in filter_words]
            
            if candidates:
                # 取第一个合适的词组合
                for c in candidates:
                    if len(hook + c) <= 9:
                        return hook + c
            
            # 如果标题没找到，从摘要找
            digest_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', digest_clean)
            candidates = [w for w in digest_words if w not in hook and w not in filter_words]
            if candidates:
                for c in candidates:
                    if len(hook + c) <= 9:
                        return hook + c
            
            # 兜底：钩子词+指南
            return (hook + "指南")[:9]
        else:
            # 钩子词本身足够长，直接用前9字
            return hook[:9]
    else:
        # 没找到钩子词，从标题提取核心信息
        # 尝试提取冒号前的主标题
        if ":" in title_clean or "：" in title:
            main_title = title_clean.split(":")[0].split("：")[0]
            main_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', main_title)
            if 3 <= len(main_title) <= 9:
                return main_title
        
        # 提取标题中的关键名词短语
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', title_clean)
        filter_words = {"这个", "那个", "那些", "这些", "什么", "怎么", "为什么", 
                      "就是", "不是", "可以", "没有", "一个", "两个", "三个"}
        candidates = [w for w in words if w not in filter_words]
        
        if candidates:
            # 组合前两个词
            title = "".join(candidates[:2])
            if len(title) > 9:
                title = title[:9]
            if len(title) >= 3:
                return title
        
        # 兜底：清理后截取前9字
        clean_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', title_clean)
        if len(clean_title) >= 3:
            return clean_title[:9]
        return "AI实战指南"


def generate_cover(title, subtitle, category="AI提效", output=None):
    """生成品牌风格封面 (900x383)"""
    W, H = 900, 383
    CENTER = W // 2
    
    img = Image.new("RGB", (W, H), DARK_BG)
    draw = ImageDraw.Draw(img)
    
    try:
        f_brand = ImageFont.truetype(FONT_PATH, 18)
        f_tag = ImageFont.truetype(FONT_PATH, 15)
        f_title = ImageFont.truetype(FONT_PATH, 56)
        f_title_small = ImageFont.truetype(FONT_PATH, 48)
        f_sub = ImageFont.truetype(FONT_PATH, 20)
        f_foot = ImageFont.truetype(FONT_PATH, 14)
    except:
        f_brand = f_tag = f_title = f_title_small = f_sub = f_foot = ImageFont.load_default()
    
    # 顶部品牌栏
    draw.rectangle([(0, 0), (W, 44)], fill=DARK_BG)
    brand_text = "美好需要创造 · WORLD CORNER"
    bb = draw.textbbox((0, 0), brand_text, font=f_brand)
    draw.text((CENTER - (bb[2]-bb[0])//2, 10), brand_text, fill="rgb(220,190,100)", font=f_brand)
    
    # 分类标签
    tag_text = f"◆ {category} ◆"
    bb = draw.textbbox((0, 0), tag_text, font=f_tag)
    tw = bb[2] - bb[0]
    tx = CENTER - tw // 2
    draw.rectangle([(tx-8, 56), (tx+tw+8, 78)], outline=GOLD, width=1)
    draw.text((tx, 58), tag_text, fill=GOLD, font=f_tag)
    
    # 标题上分割线
    draw.line([(260, 185), (640, 185)], fill=GOLD, width=2)
    
    # 标题
    title_font = f_title if len(title) <= 6 else f_title_small
    bb = draw.textbbox((0, 0), title, font=title_font)
    draw.text((CENTER - (bb[2]-bb[0])//2, 115), title, fill=GOLD, font=title_font)
    
    # 标题下分割线
    draw.line([(340, 215), (560, 215)], fill=GOLD, width=2)
    
    # 星号装饰
    draw.text((438, 232), "★", fill=GOLD, font=f_sub)
    
    # 摘要
    bb = draw.textbbox((0, 0), subtitle, font=f_sub)
    draw.text((CENTER - (bb[2]-bb[0])//2, 270), subtitle, fill="#b4b4d2", font=f_sub)
    
    # 底部栏
    draw.rectangle([(0, H-44), (W, H)], fill=DARK_BG)
    today = datetime.now().strftime("%Y.%m.%d")
    foot_text = f"{BRAND} / {today}"
    draw.text((30, 350), foot_text, fill="#8c8caa", font=f_foot)
    
    # 装饰圆点
    for x in [30, 52, 74]:
        draw.ellipse([(x, 358), (x+8, 366)], fill=GOLD)
    for x in [854, 832, 810]:
        draw.ellipse([(x, 358), (x+8, 366)], fill=GOLD)
    
    if output is None:
        # 保存到桌面
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        safe_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', title)[:10]
        output = os.path.join(desktop, f"cover_{safe_title}.jpg")
    
    os.makedirs(os.path.dirname(output), exist_ok=True)
    img.save(output, "JPEG", quality=95)
    print(f"🎨 封面已生成: {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description="获取公众号草稿并生成封面")
    parser.add_argument("--list", action="store_true", help="列出草稿列表")
    parser.add_argument("--cover", action="store_true", help="为最新草稿生成封面")
    args = parser.parse_args()
    
    token = get_access_token()
    if not token:
        print("❌ 无法获取 access_token，请检查 ~/.env_wx 或 platform-cookies.json")
        return
    
    print(f"✅ 获取到 token: {token[:20]}...")
    
    # 获取草稿列表
    result = list_drafts(token)
    if "errcode" in result and result["errcode"] != 0:
        print(f"❌ 获取草稿列表失败: {result}")
        return
    
    items = result.get("item", [])
    if not items:
        print("📭 草稿箱为空")
        return
    
    print(f"📋 共有 {len(items)} 个草稿")
    
    # 列出草稿
    for i, item in enumerate(items[:10]):
        content = item.get("content", {})
        news = content.get("news_item", [])
        if news:
            n = news[0]
            title = n.get("title", "无标题")
            digest = n.get("digest", "无摘要")
            create_time = item.get("create_time", 0)
            update_time = item.get("update_time", 0)
            if create_time:
                create_str = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M")
            else:
                create_str = "未知"
            if update_time:
                update_str = datetime.fromtimestamp(update_time).strftime("%Y-%m-%d %H:%M")
            else:
                update_str = "未知"
            print(f"\n  {i+1}. {title}")
            print(f"     📝 摘要: {digest[:50]}...")
            print(f"     📅 创建: {create_str}")
            print(f"     📅 更新: {update_str}")
            print(f"     🆔 media_id: {item.get('media_id')}")
    
    if args.list and not args.cover:
        return
    
    # 获取最新草稿详情
    latest = items[0]
    media_id = latest.get("media_id")
    print(f"\n🔍 获取最新草稿详情 (media_id: {media_id})...")
    
    detail = get_draft(token, media_id)
    if "errcode" in detail and detail["errcode"] != 0:
        print(f"❌ 获取草稿详情失败: {detail}")
        return
    
    news_items = detail.get("news_item", [])
    if not news_items:
        print("❌ 草稿内容为空")
        return
    
    draft = news_items[0]
    original_title = draft.get("title", "无标题")
    digest = draft.get("digest", "")
    content = draft.get("content", "")
    
    print(f"\n📄 原标题: {original_title}")
    print(f"📝 摘要: {digest}")
    print(f"📝 正文长度: {len(content)} 字符")
    
    # 提取吸引人标题
    appealing_title = extract_appealing_title(original_title, digest)
    
    # 提取有意义的中文摘要作为副标题
    def extract_chinese_subtitle(digest, max_len=17):
        import re
        # 按分隔符分割，找中文部分
        parts = re.split(r'[|｜\|/]', digest)
        for part in parts:
            part = part.strip()
            # 找包含中文且长度合适的部分
            chinese_chars = re.findall(r'[\u4e00-\u9fa5]', part)
            if len(chinese_chars) >= 4 and len(part) <= max_len:
                return part[:max_len]
            elif len(chinese_chars) >= 4:
                return part[:max_len]
        # 兜底：提取前17个中文字符
        chinese_only = re.sub(r'[^\u4e00-\u9fa5]', '', digest)
        if len(chinese_only) >= 4:
            return chinese_only[:max_len]
        return digest[:max_len]
    
    appealing_digest = extract_chinese_subtitle(digest)
    
    print(f"\n✨ 优化后标题: {appealing_title}")
    print(f"✨ 优化后摘要: {appealing_digest}")
    
    # 生成封面
    print("\n🎨 生成品牌风格封面...")
    cover_path = generate_cover(appealing_title, appealing_digest, "AI提效")
    print(f"✅ 封面已生成: {cover_path}")
    
    # 保存标题信息供后续使用（也放桌面）
    info = {
        "original_title": original_title,
        "optimized_title": appealing_title,
        "digest": appealing_digest,
        "media_id": media_id,
        "cover_path": cover_path,
        "create_time": datetime.now().isoformat()
    }
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    info_path = os.path.join(desktop, f"cover_info_{appealing_title[:10]}.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f"📋 信息已保存: {info_path}")


if __name__ == "__main__":
    main()
