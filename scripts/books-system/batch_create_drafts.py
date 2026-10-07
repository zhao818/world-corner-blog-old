#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量创建公众号草稿（按合集顺序，带重试 + 断点续接）
=====================================================
用途: 把《内心的修炼》合集 54 篇中未建草稿的，按 seq 顺序全部创建到公众号草稿箱，
      之后由用户自己每天手动群发。

用法:
  python batch_create_drafts.py               # 全部未建草稿的
  python batch_create_drafts.py --seq 5 6 7   # 只处理指定 seq
  python batch_create_drafts.py --status      # 查看草稿进度

特性:
  - 重试: token/封面上传/建草稿 每步失败自动重试（指数退避），网络不稳自动续
  - 断点续接: 已建草稿（status=published）的跳过；成功的立即更新 collection_plan.json
  - 顺序: 严格按 seq 升序处理
  - 逐篇隔离: 单篇失败不影响其他篇，最后汇总
"""
import os, sys, json, re, time, importlib.util, argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(SCRIPT_DIR, "collection_plan.json")


def load_plan():
    with open(PLAN, encoding="utf-8") as f:
        return json.load(f)


def save_plan(plan):
    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def retry(fn, *args, max_retries=6, label="操作", **kwargs):
    """带指数退避的重试包装器"""
    last = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last = e
            wait = min(2 ** attempt, 60) + attempt * 2
            print("  ⚠️ {}(第{}次失败: {})，{}s后重试...".format(label, attempt, e, wait))
            time.sleep(wait)
    raise last


def archive_published(p, media_id):
    """存档：内容快照 + 发布信息（与 publish_collection.py 一致）"""
    import shutil
    arc_dir = os.path.join(SCRIPT_DIR, "archive")
    os.makedirs(arc_dir, exist_ok=True)
    src = os.path.join(SCRIPT_DIR, p["source"])
    dst = ""
    if os.path.exists(src):
        fname = "{:02d}_{}.md".format(p["seq"], re.sub(r"[^\w\u4e00-\u9fff]+", "_", p["title"])[:30])
        dst = os.path.join(arc_dir, fname)
        shutil.copy2(src, dst)
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


def create_draft_one(seq):
    """为单个 seq 创建草稿（带重试），成功返回 media_id"""
    plan = load_plan()
    p = next((x for x in plan["pieces"] if x["seq"] == seq), None)
    if not p:
        print("❌ seq {} 不存在".format(seq))
        return None
    if p.get("status") == "published":
        print("⏭️ [{}] 「{}」 已建草稿，跳过".format(seq, p["title"]))
        return None

    # 动态导入发布器
    spec = importlib.util.spec_from_file_location("pd", os.path.join(SCRIPT_DIR, "publish_draft.py"))
    pd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pd)

    md_path = os.path.join(SCRIPT_DIR, p["source"])
    if not os.path.exists(md_path):
        print("❌ [{}] 文章文件不存在: {}".format(seq, md_path))
        return None
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    # 标题（≤9字）与摘要（≤17字）
    if p.get("type") == "collection":
        title = p["title"].split("：")[0][:9] if "：" in p["title"] else p["title"][:9]
    else:
        title = p["title"][:9]
    m = re.search(r"## 本章在讲什么.*?\n(.*?)(?:\n## |\Z)", md_text, re.S)
    digest = re.sub(r"[#>*\-\s]+", " ", m.group(1)).strip()[:17] if m else "《内心的修炼》合集系列"

    print("[{:02d}/{:02d}] 创建草稿: 「{}」 摘要「{}」".format(seq, plan["total"], title, digest))
    token = retry(pd.get_access_token, label="获取token")
    print("  ✅ token 获取成功")
    cover_path = retry(pd.generate_brand_cover, title, digest, "内心的修炼", label="生成封面")
    print("  ✅ 封面生成: {}".format(cover_path))
    thumb = retry(pd.upload_cover, token, cover_path, label="封面上传")
    print("  ✅ 封面上传成功")
    html = pd.md_to_html_brand(md_text)
    media_id = retry(pd.create_draft, token, title, digest, html, thumb, label="创建草稿")
    if not media_id:
        print("  ❌ 创建草稿返回空")
        return None

    # 更新状态（断点续接关键）
    p["status"] = "published"
    p["published_at"] = datetime.now().isoformat()
    p["media_id"] = media_id
    save_plan(plan)
    arc_file, arc_info = archive_published(p, media_id)
    print("  🎉 草稿创建成功! media_id: {}  存档: {}".format(media_id, arc_file))
    # 同步书级 plan.json
    if p.get("type") == "article" and p.get("book"):
        bplan = os.path.join(SCRIPT_DIR, "books", p["book"], "plan.json")
        if os.path.exists(bplan):
            with open(bplan, encoding="utf-8") as f:
                bd = json.load(f)
            for bp in bd["pieces"]:
                if bp["no"] == p.get("no"):
                    bp["status"] = "published"
                    bp["media_id"] = media_id
                    bp["published_at"] = p["published_at"]
            with open(bplan, "w", encoding="utf-8") as f:
                json.dump(bd, f, ensure_ascii=False, indent=2)
    return media_id


def show_status():
    plan = load_plan()
    done = sum(1 for p in plan["pieces"] if p.get("status") == "published")
    print("《{}》草稿进度: {}/{}\n".format(plan["collection"], done, plan["total"]))
    for p in plan["pieces"]:
        st = "✅" if p.get("status") == "published" else "⬜"
        print("  [{}] {} 「{}」{}".format(p["seq"], st, p["title"], (" ("+(p.get("published_at") or "")[:10]+")") if p.get("status")=="published" else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", nargs="*", type=int, default=None, help="只处理指定 seq")
    ap.add_argument("--status", action="store_true", help="查看进度")
    args = ap.parse_args()

    if args.status:
        show_status()
        return

    plan = load_plan()
    if args.seq:
        targets = sorted(args.seq)
    else:
        targets = [p["seq"] for p in plan["pieces"] if p.get("status") != "published"]
    if not targets:
        print("✅ 全部已建草稿，无需处理")
        return

    print("待创建草稿 {} 篇，按顺序处理: {}\n".format(len(targets), targets))
    ok = 0
    fail = []
    for seq in targets:
        try:
            r = create_draft_one(seq)
            if r:
                ok += 1
            else:
                fail.append(seq)
        except Exception as e:
            print("❌ [{}] 失败: {}".format(seq, e))
            fail.append(seq)
        time.sleep(1)  # 每篇间隔，避免触发频率限制

    print("\n=== 完成: 成功 {} / 失败 {} ===".format(ok, len(fail)))
    if fail:
        print("失败 seq: {}（重跑本命令即续接）".format(fail))
    print("草稿已按顺序进入公众号草稿箱，可自行每天手动群发。")


if __name__ == "__main__":
    main()
