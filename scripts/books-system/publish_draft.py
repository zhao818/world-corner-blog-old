#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用发布器 v2（五维系统版）：推送到公众号草稿箱（品牌排版 V4 + 品牌封面）
用法:
  python publish_draft.py schopenhauer 1         # 发布叔本华第1章
  python publish_draft.py schopenhauer 1 --force # 重发
  python publish_draft.py schopenhauer --list    # 查看进度
"""
import os, sys, json, re, argparse, importlib.util
from datetime import datetime
import requests
from html import escape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TITLES_PATH = os.path.join(SCRIPT_DIR, "collection_titles.json")

def load_collection_titles():
    """加载合集标题表（公众号标题优先）"""
    try:
        with open(TITLES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"titles": {}}

_COL_TITLES = load_collection_titles()["titles"]

APPID = "wx331b651c8159fdcb"
APPSECRET = "9b25e7466310c7971eeb777600697d3d"
AUTHOR = "美好需要创造"
COVER_TEMPLATE = os.path.expanduser("~/claude-memory/global/tools/wechat-cover-template.py")


def md_to_html_brand(body_md: str) -> str:
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


def generate_brand_cover(title, subtitle, book_cn):
    spec = importlib.util.spec_from_file_location("cover_module", COVER_TEMPLATE)
    cover = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cover)
    out = os.path.join(SCRIPT_DIR, "cover_brand.jpg")
    return cover.generate_cover(
        title=title[:9],
        subtitle=subtitle[:17],
        category=book_cn,
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


def create_draft(token, title, digest, content_html, thumb_media_id):
    """创建公众号草稿，返回 media_id"""
    body = {
        "articles": [{
            "title": title[:64],
            "author": AUTHOR,
            "digest": digest[:120],
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
    if "media_id" not in result:
        raise RuntimeError("创建草稿失败: {}".format(result))
    return result["media_id"]


def publish(book_name, no, cover_path=None, force=False):
    book_dir = os.path.join(SCRIPT_DIR, "books", book_name)
    plan_path = os.path.join(book_dir, "plan.json")
    if not os.path.exists(plan_path):
        print("❌ 未找到 plan.json")
        return False
    with open(plan_path, encoding="utf-8") as f:
        plan_data = json.load(f)
    with open(os.path.join(book_dir, "book.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    pieces = plan_data["pieces"]
    p = next((x for x in pieces if x["no"] == no), None)
    if not p:
        print("章号 {} 不存在".format(no))
        return False
    if p.get("status") != "translated" and not force:
        print("第 {} 章还没翻译（或已发布，用 --force 重发）".format(no))
        return False

    md_path = os.path.join(book_dir, "articles", p["article_file"])
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    book_cn = cfg["title_cn"]
    # 标题规则：书名首字 + 章节标题，总长<=9字（品牌约束），读得顺
    # 优先用合集标题表；无则自动生成
    col_title = _COL_TITLES.get(book_name, {}).get(str(no), "")
    if col_title:
        title = col_title[:9]
    else:
        seg = p["title"]
        if "：" in seg:
            seg = seg.split("：")[-1]
        title = (book_cn[:2] + seg[:7])[:9]
    m = re.search(r"## 本章在讲什么.*?\n(.*?)(?:\n## |\Z)", md_text, re.S)
    digest = re.sub(r"[#>*\-\s]+", " ", m.group(1)).strip()[:17] if m else "{}导读系列".format(book_cn)

    content_html = md_to_html_brand(md_text)
    print("标题: {}".format(title))
    print("摘要: {}".format(digest))

    token = get_access_token()
    print("✅ token 获取成功")

    if not cover_path:
        cover_path = generate_brand_cover(title, digest, book_cn)
        print("✅ 品牌封面生成: {}".format(cover_path))
    thumb_media_id = upload_cover(token, cover_path)
    print("✅ 封面上传成功")

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
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)
        print("🎉 草稿创建成功! media_id: {}".format(result["media_id"]))
        return True
    else:
        print("❌ 发布失败: {}".format(result))
        return False


def list_status(book_name):
    plan_path = os.path.join(SCRIPT_DIR, "books", book_name, "plan.json")
    with open(plan_path, encoding="utf-8") as f:
        plan_data = json.load(f)
    print("《{}》进度:".format(plan_data["book"]))
    for p in plan_data["pieces"]:
        st = p.get("status", "pending")
        ts = (p.get("published_at") or "")[:10]
        print("  [{:02d}] {:<30} {:<10} {}".format(p["no"], p["title"][:28], st, ts))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("book", help="书名（books/ 下目录名）")
    ap.add_argument("chapters", nargs="*", type=int)
    ap.add_argument("--cover", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        list_status(args.book)
    elif args.chapters:
        for c in args.chapters:
            publish(args.book, c, args.cover, force=args.force)
    else:
        ap.print_help()




