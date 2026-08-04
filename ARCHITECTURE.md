# 项目结构

> 已更新为 monorepo 四端现状（2026-08-04）。

```
book-buddy/
├── README.md                # 项目主文档
├── HANDOFF.md               # 交接文档
├── ARCHITECTURE.md          # 本文件
├── LICENSE                  # MIT
├── .gitignore
├── package.json             # monorepo 根（pnpm workspace 编排脚本）
├── pnpm-workspace.yaml      # workspace 声明：apps/* + packages/*
│
├── backend/                 # Python 后端（FastAPI）—— Zcode 维护
│   ├── main.py              # 入口，注册所有路由 + 中间件
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── config.py        # Pydantic Settings 配置
│   │   ├── routers/
│   │   │   ├── chat.py      # 对话（含流式 SSE）
│   │   │   ├── voice.py     # 语音转写/合成
│   │   │   ├── book.py      # 书籍上传/检索/删除
│   │   │   ├── config.py    # LLM/语音 配置管理
│   │   │   └── formula.py   # 公式渲染（LaTeX → SVG/PNG）
│   │   ├── services/
│   │   │   ├── llm.py       # LLM（Qwen-VL / OpenAI 兼容：智谱 GLM）
│   │   │   ├── voice.py     # ASR/TTS（DashScope qwen3-asr / cosyvoice）
│   │   │   ├── rag.py       # PDF 解析 + Chroma 向量检索
│   │   │   ├── formula.py   # matplotlib mathtext 公式渲染
│   │   │   └── config_store.py  # .env 持久化 + 热更新
│   │   ├── middleware/
│   │   │   └── auth.py      # 可选 token 鉴权（AUTH_TOKEN 控制）
│   │   └── models/          # Pydantic 请求/响应模型
│   └── tests/               # pytest（57 测试）
│
├── packages/
│   └── core/                # 跨端共享层（纯 TS，零 DOM/wx 依赖）—— Zcode 维护
│       ├── src/
│       │   ├── types.ts     # ChatMessage / ChatRequest / BookInfo 等类型
│       │   ├── api.ts       # API 路径常量 + 请求体组装（snake_case 映射）
│       │   ├── sse.ts       # SSEParser（纯字符串帧解析）
│       │   ├── tts.ts       # SentenceStreamer（按句切分流式朗读）
│       │   ├── platform.ts  # 平台适配接口定义（ChatTransport 等，Z1 冻结）
│       │   └── index.ts     # 统一导出
│       ├── test/            # node:test 契约测试（14 测试）
│       └── dist/            # tsc 构建产物
│
├── apps/
│   ├── web/                 # Web 端（Vue 3 + Vite + TS）—— Zcode 维护
│   │   └── src/
│   │       ├── platform/    # core 平台接口的 Web 实现（ChatTransport 等）
│   │       ├── components/  # ChatInterface / CameraCapture / BookSelector / SettingsPanel
│   │       ├── utils/       # render.ts（marked+KaTeX+DOMPurify）、audio.ts、tts.ts
│   │       └── api/         # client.ts（HTTP 请求封装）
│   │
│   ├── mp/                  # 微信小程序（uni-app Vue3）—— Kimi 维护
│   │   └── src/
│   │       ├── pages/index/ # 对话页
│   │       └── platform/    # chat.ts（wx.request chunked SSE adapter）
│   │
│   └── desktop/             # 桌面端（Tauri 2 壳）—— Kimi 维护
│
├── scripts/
│   ├── start.mjs            # 一键启动脚本（--dev / --desktop）
│   └── make_test_pdf.py     # 测试 PDF 生成
│
├── docs/
│   ├── migration-multi-platform.md   # 多端迁移方案蓝图
│   ├── TASK_SPLIT_MULTI_PLATFORM.md  # 双智能体任务拆分与协调记录
│   ├── CHANGES_REVIEW_ROUND2.md      # RAG/LLM/配置审阅
│   ├── CHANGES_REVIEW_ROUND3.md      # 语音链路审阅
│   ├── CHANGES_REVIEW_ROUND4.md      # 多端迁移 Z1~Z5 实现
│   └── ...
│
└── .github/
    └── workflows/
        └── ci.yml           # GitHub Actions CI
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+, FastAPI, PyMuPDF, Chroma, matplotlib, DashScope |
| LLM | 智谱 GLM-4.6V（默认）/ 通义千问 Qwen-VL / 任意 OpenAI 兼容 |
| 共享层 | TypeScript, node:test |
| Web | Vue 3, Vite, marked, KaTeX, DOMPurify |
| 小程序 | uni-app (Vue 3), 微信小程序 |
| 桌面 | Tauri 2（加载 Web 构建产物） |
| 包管理 | pnpm workspace |

## 常用命令

```bash
# 安装所有依赖
pnpm install

# 一键启动（后端 + 前端）
pnpm start            # 生产模式
pnpm start:dev        # 开发模式（热重载）

# 单独启动
pnpm dev:web          # Web 前端
pnpm dev:mp           # 小程序
pnpm dev:backend      # 后端
pnpm dev:desktop      # 桌面端

# 构建
pnpm build            # core + web + mp-weixin
pnpm build:desktop    # 含桌面端

# 测试
pnpm test             # core 测试 + 后端 pytest
```

## 平台适配架构

```
packages/core（平台无关）
  ├── 类型 / API 契约 / SSE 解析 / 句子切分
  └── platform.ts 接口定义（ChatTransport / PhotoCapture / AudioRecorder / AudioPlayer）
         ▲
         │ 各端实现
  ┌──────┼──────────┬──────────┐
  │      │          │          │
apps/web  apps/mp   apps/desktop
(fetch)   (wx.req)  (Tauri)
```
