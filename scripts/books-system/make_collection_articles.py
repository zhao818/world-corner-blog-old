#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成合集开篇引言 + 完结篇（走 18001 代理）"""
import os, json, urllib.request

API = "http://127.0.0.1:18001/v1/messages"
MODEL = "claude-sonnet-4-6"
AUTH = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")

def call_api(prompt, max_tokens=4096, max_retries=5):
    import time
    body = json.dumps({"model": MODEL, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    last = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(API, data=body, headers={
                "Content-Type": "application/json", "x-api-key": AUTH, "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            parts = data.get("content", [])
            text = "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
            if text: return text
            last = "空响应"
        except Exception as e:
            last = str(e)
        wait = min(2 ** attempt, 60)
        print("  ⚠️ 第{}次失败({})，{}s后重试...".format(attempt, last, wait))
        time.sleep(wait)
    raise RuntimeError("失败: {}".format(last))

intro_prompt = """你是一位人生哲学实践导师。请为公众号合集《内心的修炼》写一篇开篇引言文章，向读者介绍这套内容体系。

背景：这个合集用五本经典书组成一套完整的心性修炼体系，共34篇文章：
① 叔本华《人生的智慧》——断舍离：过滤外界噪音
② 奥勒留《沉思录》——立根本：锻造内在城堡
③ 王阳明《传习录》——炼心术：事上磨练、知行合一（核心）
④ 萨特《存在主义是一种人道主义》——破执念：摆脱自欺、果断担当
⑤ 福柯《规训与惩罚》——明规则：看透权力规则

每篇文章都带一个「✦ 事上磨练」本周行动任务，边读边练。

请按以下结构输出（用 Markdown，全文 1200-1800 字）：

# 《内心的修炼》| 这套合集要做什么

## 为什么是这五本书
讲清楚五本书组成一条从外到内、再由内而外的成长弧线（断舍离→立根本→炼心术→破执念→明规则）。

## 这不是哲学课，是实操指南
说明合集的定位：不是学术讲解，而是用经典打磨心性的实践手册。

## 怎么用这套合集
说明使用方式：每周3篇、每篇带事上磨练任务、写反思记录。

## 你将从这里得到什么
给读者的承诺：从内在精神防守，到实操实战，再到宏观系统洞察的完整闭环。

要求：语言有感染力、贴近生活、让人想订阅这个合集。"""
outro_prompt = """你是一位人生哲学实践导师。请为公众号合集《内心的修炼》写一篇完结篇（收官文），为整套体系做总结。

背景：这个合集用五本经典书组成心性修炼体系，34篇文章全部完成：
① 叔本华《人生的智慧》——断舍离：过滤外界噪音，轻装上阵
② 奥勒留《沉思录》——立根本：锻造内在城堡，稳住底盘
③ 王阳明《传习录》——炼心术：事上磨练、知行合一（核心）
④ 萨特《存在主义是一种人道主义》——破执念：摆脱自欺、果断担当
⑤ 福柯《规训与惩罚》——明规则：看透权力规则，聪明地活

请按以下结构输出（用 Markdown，全文 1200-1800 字）：

# 《内心的修炼》| 五阶段收官

## 回望这条修炼之路
回顾五个阶段的递进逻辑：从外断噪音到内立根本，再到事上磨练、果断担当、看透规则。

## 五个阶段的收获
每个阶段 2-3 句总结核心收获（断舍离/立根本/炼心术/破执念/明规则）。

## 事上磨练：真正的修行在生活里
回顾每篇的「事上磨练」任务的意义：心性不是想出来的，是做出来的。

## 下一步：把修炼变成习惯
给读者的行动号召：如何把这套体系变成长期习惯，继续成长。

要求：有总结感、有力量感、鼓励读者继续前行。"""

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books", "_collection")
os.makedirs(out_dir, exist_ok=True)

print("生成开篇引言...")
intro = call_api(intro_prompt)
with open(os.path.join(out_dir, "00_开篇引言.md"), "w", encoding="utf-8") as f:
    f.write(intro)
print("✅ 开篇引言已保存")

print("生成完结篇...")
outro = call_api(outro_prompt)
with open(os.path.join(out_dir, "35_完结篇.md"), "w", encoding="utf-8") as f:
    f.write(outro)
print("✅ 完结篇已保存")
