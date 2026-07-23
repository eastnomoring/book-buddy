# 项目结构

```
book-buddy/
├── README.md                # 项目主文档（给用户看）
├── HANDOFF.md               # 交接文档（给下一个开发者/智能体看）
├── ARCHITECTURE.md          # 本文件：目录结构说明
├── LICENSE                  # MIT
├── .gitignore
│
├── backend/                 # Python 后端
│   ├── main.py              # FastAPI 入口
│   ├── requirements.txt
│   ├── pyproject.toml       # 可选：现代 Python 项目配置
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py        # 配置管理（API Key 等）
│   │   ├── routers/
│   │   │   ├── chat.py      # 对话接口
│   │   │   ├── voice.py     # 语音接口
│   │   │   └── book.py      # 书籍上传/解析
│   │   ├── services/
│   │   │   ├── llm.py       # LLM 封装（Qwen/DeepSeek）
│   │   │   ├── asr.py       # 语音识别（Qwen-Audio）
│   │   │   ├── tts.py       # 语音合成（流式）
│   │   │   ├── rag.py       # RAG 管道（向量检索）
│   │   │   ├── pdf_parser.py# PDF 解析（marker/nougat）
│   │   │   └── mcp_client.py# MCP 客户端封装
│   │   └── models/          # Pydantic 模型
│   │       ├── chat.py
│   │       └── book.py
│   ├── data/                # 本地数据（书籍 PDF、向量库）
│   │   └── books/
│   └── tests/
│
├── frontend/                # Web 前端
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue          # 或 App.tsx（框架待定）
│   │   ├── components/
│   │   │   ├── Camera.vue   # 摄像头组件
│   │   │   ├── Chat.vue     # 对话界面
│   │   │   ├── VoiceButton.vue
│   │   │   └── Formula.vue  # KaTeX 公式渲染
│   │   ├── api/
│   │   │   └── client.ts    # 后端 API 调用
│   │   └── stores/          # 状态管理（Pinia / Zustand）
│   └── public/
│
├── docs/                    # 文档
│   ├── setup.md             # 详细安装指南
│   ├── mcp-integration.md   # MCP 接入说明
│   └── roadmap.md           # 路线图详解
│
└── scripts/                 # 辅助脚本
    ├── ingest_book.py       # 导入一本书到向量库
    └── test_voice.py        # 语音链路测试
```

## 关键模块说明

### backend/app/services/llm.py
- 封装 Qwen-VL / DeepSeek 多模态调用
- 支持图像 + 文本混合输入
- 流式输出（SSE）

### backend/app/services/rag.py
- 书籍 PDF 解析（按章节分块）
- 向量化（sentence-transformers / text-embedding）
- 检索：给定问题 + 当前页信息，返回相关段落

### backend/app/services/mcp_client.py
- MCP 客户端管理（连接多个 MCP server）
- 封装为可调用工具：代码执行、Anki、笔记等

### frontend/src/components/Camera.vue
- getUserMedia 调用摄像头
- 拍照 → 上传到后端
- 显示预览与当前页定位结果

### frontend/src/components/Chat.vue
- 对话界面：消息列表 + 输入框
- KaTeX 渲染数学公式
- 加载状态、错误处理

---

## 数据流（一次问答）

```
用户拍照/语音提问
       │
       ▼
前端：Camera/VoiceButton → 捕获图像/音频
       │
       ▼
POST /api/chat { image: base64, audio: base64, text: "" }
       │
       ▼
后端：
  1. ASR 音频 → 文本
  2. 视觉模型识别页码/章节
  3. RAG 检索相关段落
  4. 构建提示词（问题 + 书籍上下文）
  5. 调用 LLM（流式）
  6. TTS 文本 → 音频（流式）
       │
       ▼
前端：Chat 组件显示回答，播放 TTS 音频
```

---

## 后续演进

- **部署**：可用 Docker Compose 打包前后端，或用 Tauri 套壳为桌面应用
- **云端**：前端部署到 Vercel/Cloudflare，后端可本地跑或部署到云服务器
- **移动端**：如需原生 App，可用 Flutter 重写前端，后端不变

---

## 代码风格约定

- Python：遵循 PEP 8，类型注解，docstring 用 Google 风格
- TypeScript/Vue：组件命名 PascalCase，API 调用集中到 `api/` 目录
- 提交信息：遵循 Conventional Commits（feat/fix/docs/refactor）