# 搜索 MCP —— 选型记录（Z3）

> **状态**：调研完成，**本轮暂缓接入**。笔记工具（本地 markdown）已落地；搜索等国内可用 API / 配额方案明确后再做。
> **日期**：2026-08-04
> **归属**：原 Zcode Z3；Cursor 接手后补齐本文档。

---

## 1. 目标

书上没讲透的背景知识自动补充（HANDOFF §5）。LLM 在讲解时若发现需要外部背景，可调用搜索工具拿摘要，再融入回答。

---

## 2. 候选

| 方案 | 国内可用性 | 备注 |
|---|---|---|
| **Brave Search API** | 需翻墙/境外 | MCP 生态有现成 server；个人自用不稳 |
| **Tavily** | 需境外卡 | 面向 RAG 的搜索 API，有额度 |
| **Bing Web Search** | 国内受限 | 微软认知服务，申请门槛 |
| **博查 / 秘塔等国内搜索 API** | 较好 | 需调研具体 OpenAPI 与授权 |
| **DuckDuckGo html 抓取** | 不稳定 | 无官方 API，易被封，不建议 |
| **不做搜索，改用模型内建知识** | 最好 | 概率论教材场景多数可由书内 RAG + 模型知识覆盖 |

---

## 3. 决策（本轮）

**暂缓接入搜索工具。** 理由：

1. 伴学主路径是「书内符号体系 + RAG」，外部搜索不是 MVP 阻塞项
2. 国内稳定、可开源分发的搜索 API 尚未选定（避免把用户绑到难申请的境外 Key）
3. 笔记沉淀（本地 markdown）已能覆盖「学完归档」需求

后续若用户指定搜索提供商（或自备 Key），再按 S4/Anki 同一套 `registry` + tool_loop 接入，预计 0.5～1 天。

---

## 4. 若后续接入的接口草图

```text
name: web_search
params: { query: string, max_results?: number }
return: { text: "标题/摘要列表…", images: [] }
config: SEARCH_ENABLED=false, SEARCH_PROVIDER=..., SEARCH_API_KEY=...
```

安全：仅返回摘要文本，不执行页面脚本；结果截断 ≤2KB 再回注 LLM。
