# Anki MCP 接入 —— 选型记录（Z2）

> **任务来源**：`docs/TASK_SPLIT_MULTI_PLATFORM.md` §9 Z2
> **文档日期**：2026-08-04
> **状态**：选型已定，实现待做

---

## 1. 需求

学完一节后自动生成 Anki 抽认卡（HANDOFF §5 / README「规划中」）。LLM 通过 tool loop 调用 Anki 工具，把讲解转化为「正面问题 + 书中出处，背面讲解」的卡片。

## 2. 调研结论

### 2.1 AnkiConnect

- Anki 官方推荐的 HTTP API 插件（插件码 **2055492159**），默认 `http://localhost:8765`
- 请求格式：`POST {"action":"addNote","version":6,"params":{"note":{...}}}`
- 关键 action：`addNote`（建卡）、`deckNames`（列牌组）、`modelNames`（列模型）、`findCards`（查卡）
- **前提**：Anki GUI + AnkiConnect 插件必须在跑

### 2.2 ankimcp/anki-mcp-server（~416 stars）

- 纯代理，HTTP 调本地 AnkiConnect，暴露 42 个 MCP 工具
- 仍要求 Anki + AnkiConnect 在跑，未消除部署复杂度
- 对本项目过重（只需要 addNote + 少量查询）

### 2.3 Headless Anki

- `ankimcp/headless-anki` Docker 镜像，Qt VNC 模拟显示，AnkiConnect 暴露 8765
- 适合服务器部署，但 AnkiWeb 同步较麻烦
- 个人自用场景（本地开 Anki）暂不需要

### 2.4 卡片模板

- Basic（Front/Back）不够：缺「出处」字段
- **自定义模型**，字段：`Question`、`Source`（书名+页码/章节）、`Answer`
- Anki 原生支持 LaTeX：`[$]...[$]`（行间 `[$$]...[$$]`）

## 3. 选型决策

**自建薄 MCP 工具，直连 AnkiConnect HTTP API。** 理由：

1. 只需 `addNote` + 牌组/模型自动创建，代码量小（<100 行），零外部依赖
2. ankimcp server 暴露 42 个工具过重，且未消除「Anki 在跑」的前提
3. 保持与 S4 代码执行一致的架构：本地注册工具，走 tool_loop

### 用户侧前置条件

1. 安装 Anki（桌面端）
2. 安装 AnkiConnect 插件（工具 → 插件 → 获取插件 → 2055492159）
3. 保持 Anki 开启
4. 后端 `.env` 设 `ANKI_ENABLED=true`

### 安全/健壮性

- AnkiConnect 默认仅本机访问（localhost:8765），无认证
- 工具调用失败（Anki 没开）时返回明确错误提示，不阻塞对话
- 卡片内容做基本 HTML 转义，防注入 Anki 模板

## 4. 工具设计

### `create_flashcard`

```json
{
  "name": "create_flashcard",
  "description": "创建一张 Anki 抽认卡。学完一个知识点后调用。",
  "parameters": {
    "type": "object",
    "properties": {
      "question": {"type": "string", "description": "正面问题（简洁）"},
      "answer": {"type": "string", "description": "背面讲解（可含 LaTeX：[$]x^2[$]）"},
      "source": {"type": "string", "description": "出处：书名+页码/章节"},
      "tags": {"type": "array", "items": {"type": "string"}, "description": "标签"}
    },
    "required": ["question", "answer"]
  }
}
```

行为：
- 自动确保牌组 `Book Buddy` 存在（不存在则创建）
- 自动确保自定义模型 `BookBuddy Card` 存在（字段 Question/Source/Answer），不存在则创建
- 调 `addNote` 建卡
- 返回成功/失败信息给 LLM

## 5. 不做什么

- 不引入 ankimcp server（过重）
- 不做 headless Anki（个人自用不需要）
- 不做批量建卡（首版一次一张，LLM 逐个调）
- 不做 AnkiWeb 同步（用户手动同步）
