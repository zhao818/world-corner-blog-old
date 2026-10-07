#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合集发布队列管理器：按顺序发布《内心的修炼》36 篇，自动留痕
用法:
  python publish_collection.py --status     # 查看发布进度（下一篇是谁）
  python publish_collection.py next         # 发布下一篇（自动找第一个待发）
  python publish_collection.py 3            # 发布指定序号
  发布成功会自动更新 collection_plan.json 的 status/media_id/published_at
"""
import os, sys, json, re, importlib.util, argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(SCRIPT_DIR, "collection_plan.json")


def load_plan():
    with open(PLAN, encoding="utf-8") as f:
        return json.load(f)


def save_plan(plan):
    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def archive_published(p, media_id):
    """发布成功后存档：内容快照 + 发布信息"""
    import shutil
    arc_dir = os.path.join(SCRIPT_DIR, "archive")
    os.makedirs(arc_dir, exist_ok=True)
    # 内容快照（复制源 md）
    src = os.path.join(SCRIPT_DIR, p["source"])
    if os.path.exists(src):
        fname = "{:02d}_{}.md".format(p["seq"], re.sub(r"[^\w\u4e00-\u9fff]+", "_", p["title"])[:30])
        dst = os.path.join(arc_dir, fname)
        shutil.copy2(src, dst)
    else:
        dst = ""
    # 发布信息 JSON
    info = {
        "seq": p["seq"], "type": p.get("type"), "title": p["title"],
        "book": p.get("book"), "no": p.get("no"),
        "media_id": media_id,
        "published_at": p.get("published_at"),
        "source": p["source"],
        "archived_file": dst,
    }
    info_path = os.path.join(arc_dir, "{:02d}_info.json".format(p["seq"]))
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    return dst, info_path


def next_pending(plan):
    for p in plan["pieces"]:
        if p.get("status") != "published":
            return p
    return None


def show_status():
    plan = load_plan()
    print("《{}》发布进度: {}/{}\n".format(plan["collection"],
          sum(1 for p in plan["pieces"] if p.get("status") == "published"), plan["total"]))
    for p in plan["pieces"]:
        st = "✅" if p.get("status") == "published" else "⬜"
        src = p.get("book", "合集") if p.get("type") == "article" else "合集"
        ts = (p.get("published_at") or "")[:10]
        print("  [{:02d}] {} {} 「{}」{}".format(p["seq"], st, src, p["title"], " ("+ts+")" if ts else ""))
    np_ = next_pending(plan)
    if np_:
        print("\n➡️ 下一篇该发: [{}] 「{}」".format(np_["seq"], np_["title"]))
    else:
        print("\n🎉 全部发布完成！")


def publish_one(seq):
    plan = load_plan()
    p = next((x for x in plan["pieces"] if x["seq"] == seq), None)
    if not p:
        print("序号 {} 不存在".format(seq))
        return False
    if p.get("status") == "published":
        print("⚠️ [{}] 「{}」 已发布过 ({}). 如需重发请手动改状态".format(seq, p["title"], (p.get("published_at") or "")[:19]))
        return False

    # 动态导入发布器
    spec = importlib.util.spec_from_file_location("pd", os.path.join(SCRIPT_DIR, "publish_draft.py"))
    pd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pd)

    # 找到 md 文件
    src = p["source"]
    md_path = os.path.join(SCRIPT_DIR, src)
    if not os.path.exists(md_path):
        print("❌ 文章文件不存在: {}".format(md_path))
        return False

    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    # 取标题（合集文章用首行#，正文用标题表）
    if p.get("type") == "collection":
        title = p["title"].split("：")[0][:9] if "：" in p["title"] else p["title"][:9]
    else:
        title = p["title"][:9]
    # 摘要
    import re
    m = re.search(r"## 本章在讲什么.*?\n(.*?)(?:\n## |\Z)", md_text, re.S)
    digest = re.sub(r"[#>*\-\s]+", " ", m.group(1)).strip()[:17] if m else "《内心的修炼》合集系列"
    print("发布: [{}] 「{}」".format(seq, title))
    print("摘要: {}".format(digest))

    try:
        token = pd.get_access_token()
        print("✅ token 获取成功")
        cover_path = pd.generate_brand_cover(title, digest, "内心的修炼")
        print("✅ 品牌封面生成")
        thumb = pd.upload_cover(token, cover_path)
        print("✅ 封面上传成功")
        html = pd.md_to_html_brand(md_text)
        result = pd.create_draft(token, title, digest, html, thumb)
        if result:
            media_id = result
            p["status"] = "published"
            p["published_at"] = datetime.now().isoformat()
            p["media_id"] = media_id
            save_plan(plan)
            arc_file, arc_info = archive_published(p, media_id)
            print("   存档: {} + {}".format(arc_file, arc_info))
            # 同步更新该书 plan.json
            if p.get("type") == "article":
                bplan = os.path.join(SCRIPT_DIR, "books", p["book"], "plan.json")
                with open(bplan, encoding="utf-8") as f:
                    bd = json.load(f)
                for bp in bd["pieces"]:
                    if bp["no"] == p["no"]:
                        bp["status"] = "published"
                        bp["media_id"] = media_id
                        bp["published_at"] = p["published_at"]
                with open(bplan, "w", encoding="utf-8") as f:
                    json.dump(bd, f, ensure_ascii=False, indent=2)
            print("🎉 [{}] 「{}」 发布成功! media_id: {}".format(seq, p["title"], media_id))
            print("   痕迹已记录: collection_plan.json + books/{}/plan.json".format(p.get("book", "_collection")))
            return True
    except Exception as e:
        print("❌ 发布失败: {}".format(e))
        return False
    return False


def main():
    argv = sys.argv[1:]
    if not argv:
        print("用法: python publish_collection.py <next|序号|--status>")
        return
    cmd = argv[0]
    if cmd in ("--status", "status", "-s", "list"):
        show_status()
    elif cmd == "next":
        plan = load_plan()
        np_ = next_pending(plan)
        if not np_:
            print("🎉 全部发布完成！")
            return
        print("➡️ 发布下一篇: [{}] 「{}」".format(np_["seq"], np_["title"]))
        publish_one(np_["seq"])
    elif cmd.isdigit():
        publish_one(int(cmd))
    else:
        print("未知命令: {}".format(cmd))
        print("用法: python publish_collection.py <next|序号|--status>")


if __name__ == "__main__":
    main()



