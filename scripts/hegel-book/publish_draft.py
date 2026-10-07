#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布脚本 v2（品牌排版版）：把已翻译的章节 Markdown 推送到微信公众号「美好需要创造」草稿箱
复用积累技能:
  - V4-Final 排版模板 (catalog/platforms/base.py md_to_html): 深海蓝标题块 #1a1a2e + 暖金引用 #c8a03c + ✦金句
  - 品牌封面死框架 (claude-memory/global/tools/wechat-cover-template.py): 900x383 死参数
用法:
  python publish_draft.py 1              # 发布第 1 章到草稿箱
  python publish_draft.py 1 --force      # 重发已发布的章节（产生新草稿）
  python publish_draft.py 1 --cover path.jpg   # 指定封面图
  python publish_draft.py --list         # 查看当前进度
"""
import os, sys, json, re, argparse, importlib.util
from datetime import datetime
import requests
from html import escape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "articles")
PLAN = os.path.join(SCRIPT_DIR, "plan.json")

APPID = "wx331b651c8159fdcb"
APPSECRET = "9b25e7466310c7971eeb777600697d3d"
AUTHOR = "美好需要创造"
COVER_TEMPLATE = os.path.expanduser("~/claude-memory/global/tools/wechat-cover-template.py")

CN_TITLES = {
    1: "导论：论科学认识", 2: "第一章 意识", 3: "第二章 自我意识",
    4: "理性（引论）", 5: "观察的理性", 6: "理性的现实化",
    7: "自在而自为的个体性", 8: "精神（引论）", 9: "真实的精神：伦理秩序",
    10: "自我异化的精神：教化", 11: "异化精神的世界", 12: "启蒙",
    13: "绝对自由与恐怖", 14: "宗教（引论）", 15: "自然宗教",
    16: "艺术宗教", 17: "天启宗教", 18: "绝对知识",
}


def md_to_html_brand(body_md: str) -> str:
    """V4-Final 品牌排版模板：深海蓝标题块 + 暖金引用 + ✦金句"""
    lines = body_md.split("\n")
    html = []
    for line in lines:
        line = line.rstrip()
        if line.startswith("## ") and not line.startswith("### "):
            html.append(f'<h2 style="font-size:20px;background:#1a1a2e;color:#fff;padding:12px 20px;border-radius:6px;margin-bottom:24px;font-weight:600;border-left:4px solid #c8a03c;">{escape(line[3:])}</h2>')
        elif line.startswith("### "):
            html.append(f'<h3 style="font-size:17px;color:#1a1a2e;font-weight:600;margin-bottom:8px;">{escape(line[4:])}</h3>')
        elif line.startswith("✦"):
            html.append(f'<p style="font-size:15px;color:#c8a03c;line-height:1.8;padding:12px 16px;background:#f8f6f2;border-radius:4px;margin:16px 0;">{escape(line)}</p>')
        elif line.strip().startswith(">"):
            text = line.strip()[1:].strip()
            html.append(f'<p style="font-size:15px;color:#666;line-height:1.8;padding:16px 20px;background:#f8f6f2;border-left:3px solid #c8a03c;border-radius:4px;margin-bottom:40px;">{escape(text)}</p>')
        elif line.strip() == "":
            pass
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            html.append(f"<p style=\"margin:5px 0;padding-left:2em;color:#444;\">• {escape(line.strip()[2:])}</p>")
        elif line.strip().startswith("|"):
            pass
        else:
            html.append(f"<p style=\"color:#444;margin-bottom:20px;line-height:1.8;\">{escape(line)}</p>")
    return "".join(html)


def generate_brand_cover(title: str, subtitle: str) -> str:
    """调用品牌封面死框架生成 900x383 封面"""
    spec = importlib.util.spec_from_file_location("cover_module", COVER_TEMPLATE)
    cover = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cover)
    out = os.path.join(SCRIPT_DIR, "cover_brand.jpg")
    return cover.generate_cover(
        title=title[:9],
        subtitle=subtitle[:17],
        category="哲学",
        date=datetime.now().strftime("%Y.%m.%d"),
        output=out,
    )


def get_access_token():
    r = requests.get("https://api.weixin.qq.com/cgi-bin/token",
                     params={"grant_type": "client_credential", "appid": APPID, "secret": APPSECRET}, timeout=20)
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError("获取 token 失败: {}".format(data))
    return data["access_token"]


def upload_cover(token, cover_path):
    url = "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={}&type=image".format(token)
    with open(cover_path, "rb") as f:
        resp = requests.post(url, files={"media": (os.path.basename(cover_path), f, "image/jpeg")}, timeout=60)
    data = resp.json()
    if "media_id" not in data:
        raise RuntimeError("上传封面失败: {}".format(data))
    return data["media_id"]


def publish(no, cover_path=None, force=False):
    with open(PLAN, encoding="utf-8") as f:
        plan_data = json.load(f)
    pieces = plan_data["pieces"]
    p = next((x for x in pieces if x["no"] == no), None)
    if not p:
        print("章号 {} 不存在".format(no))
        return False
    if p.get("status") != "translated" and not force:
        print("第 {} 章还没翻译（或已发布，用 --force 重发），先运行: python translate_guide.py {}".format(no, no))
        return False

    md_path = os.path.join(OUT_DIR, p["article_file"])
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    cn = CN_TITLES.get(no, p["title"])
    title = cn[:9]
    m = re.search(r"## 本章在讲什么.*?\n(.*?)(?:\n## |\Z)", md_text, re.S)
    digest = re.sub(r"[#>*\-\s]+", " ", m.group(1)).strip()[:17] if m else "黑格尔《精神现象学》导读系列"

    content_html = md_to_html_brand(md_text)

    print("标题: {}".format(title))
    print("摘要: {}".format(digest))

    token = get_access_token()
    print("✅ token 获取成功")

    if not cover_path:
        cover_path = generate_brand_cover(title, digest)
        print("✅ 品牌封面生成: {}".format(cover_path))
    thumb_media_id = upload_cover(token, cover_path)
    print("✅ 封面上传成功: {}".format(thumb_media_id))

    body = {
        "articles": [{
            "title": title,
            "author": AUTHOR,
            "digest": digest,
            "content": content_html,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }]
    }
    r = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/add?access_token={}".format(token),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=60,
    )
    result = r.json()
    if "media_id" in result:
        p["status"] = "published"
        p["media_id"] = result["media_id"]
        p["published_at"] = datetime.now().isoformat()
        with open(PLAN, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)
        print("🎉 草稿创建成功! media_id: {}".format(result["media_id"]))
        print("   公众号后台 -> 草稿箱 -> 可预览/群发")
        return True
    else:
        print("❌ 发布失败: {}".format(result))
        return False


def list_status():
    with open(PLAN, encoding="utf-8") as f:
        plan_data = json.load(f)
    print("{:<4} {:<32} {:<12} {}".format("章", "标题", "状态", "发布时间"))
    for p in plan_data["pieces"]:
        st = p.get("status", "pending")
        ts = (p.get("published_at") or "")[:10]
        print("{:<4} {:<32} {:<12} {}".format(p["no"], CN_TITLES.get(p["no"], p["title"])[:30], st, ts))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="*", type=int, help="要发布的章节号")
    ap.add_argument("--cover", default=None, help="封面图路径")
    ap.add_argument("--force", action="store_true", help="允许重发已发布章节")
    ap.add_argument("--list", action="store_true", help="查看进度")
    args = ap.parse_args()
    if args.list:
        list_status()
    elif args.chapters:
        for c in args.chapters:
            publish(c, args.cover, force=args.force)
    else:
        ap.print_help()
