# 黑格尔《精神现象学》拆书成文框架

> 把一本英文哲学书，拆成 18 篇中文导读文章，每天发一篇到公众号草稿箱。
> 边学边读边发文，一鱼两吃。

## 流水线总览

```
split_book.py  →  chapters/   (18 个章节英文原文)
translate_guide.py  →  articles/  (18 篇中文导读 Markdown)
publish_draft.py  →  公众号「美好需要创造」草稿箱
plan.json  ←  全流程状态追踪 (pending → translated → published)
```

## 使用步骤（每天一篇）

### 1. 翻译下一章
```powershell
python translate_guide.py 2     # 翻译第 2 章（导论已完成）
```
> 想批量：`python translate_guide.py 2 3 4` 或 `--all`

### 2. 检查译文（可手动润色 articles/ 下的 md 文件）

### 3. 发布到公众号草稿箱
```powershell
python publish_draft.py 2
```
> 发布后到公众号后台 → 草稿箱 → 预览确认 → 群发

### 4. 查看进度
```powershell
python publish_draft.py --list
```

## 文件说明

| 文件 | 作用 |
|---|---|
| `split_book.py` | 拆书（已跑完，章节固定） |
| `translate_guide.py` | 调本地 18001 代理（DeepSeek V4）做导读式翻译 |
| `publish_draft.py` | 推送到公众号草稿箱（token → 封面 → draft/add） |
| `make_cover.py` | 生成默认封面 cover_default.jpg |
| `plan.json` | 18 章状态清单（唯一状态源） |
| `chapters/` | 英文原文（勿动） |
| `articles/` | 中文导读 Markdown（可编辑） |

## 公众号配置

- APPID: `wx331b651c8159fdcb`（写死在 publish_draft.py，与 push_draft.py 一致）
- APPSECRET: 写死在脚本中
- 如果 token 失效，公众号后台重置 secret 后同步改脚本

## 翻译说明

- 引擎：本地 `http://127.0.0.1:18001`（OpenCode-Go 代理 → DeepSeek V4）
- 模型：`claude-sonnet-4-6`（代理映射到 DeepSeek V4 Flash）
- 每篇结构：本章在讲什么 / 核心观点解读 / 原文精译 / 金句 / 读后思考
- 章节文本过长时自动截取头+中+尾（token 限制内）

## 18 章进度

| # | 章节 | 状态 |
|---|---|---|
| 1 | 导论：论科学认识 | ✅ 已翻译 |
| 2 | 第一章 意识 | ⬜ |
| 3 | 第二章 自我意识 | ⬜ |
| 4 | 理性（引论） | ⬜ |
| 5 | 观察的理性 | ⬜ |
| 6 | 理性的现实化 | ⬜ |
| 7 | 自在而自为的个体性 | ⬜ |
| 8 | 精神（引论） | ⬜ |
| 9 | 真实的精神：伦理秩序 | ⬜ |
| 10 | 自我异化的精神：教化 | ⬜ |
| 11 | 异化精神的世界 | ⬜ |
| 12 | 启蒙 | ⬜ |
| 13 | 绝对自由与恐怖 | ⬜ |
| 14 | 宗教（引论） | ⬜ |
| 15 | 自然宗教 | ⬜ |
| 16 | 艺术宗教 | ⬜ |
| 17 | 天启宗教 | ⬜ |
| 18 | 绝对知识 | ⬜ |
