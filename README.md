# Book Buddy

> **Read any book with an AI companion.**
> 
> 面向自学者读硬书的 AI 伴读系统 —— 它能看到你读的页面、听懂你的追问、用书中的符号体系给你讲明白。

---

## 为什么做这个？

市面上的 "AI 家教" 都是面向**写作业的学生**（解题、批改、讲题）。

但真正读一本硬书（概率论、算法导论、哲学原著……）时，你需要的是：
- **它知道你在读哪一页**，不用每次解释上下文
- **用书中的定义和符号体系回答**，而不是泛泛的网络知识
- 学完自动沉淀成**可复习的卡片和笔记**

Book Buddy 就是为这个场景设计的。

---

## 核心功能

| 功能 | 状态 |
|---|---|
| 📷 摄像头拍书页，自动定位当前页/章节 | Planned |
| 🎙️ 语音提问，"手不离书"直接追问 | Planned |
| 📖 书籍知识库（RAG），用书中的符号体系回答 | Planned |
| 🧪 MCP 代码执行：概率模拟、可视化验证 | Planned |
| 🗂️ 自动生成 Anki 卡片 + Obsidian 笔记 | Planned |
| 🌐 本地 Web 应用，浏览器打开即用 | Planned |

---

## 架构

```
┌──────────────── 浏览器（UI 层，零平台代码） ────────────────┐
│  摄像头 getUserMedia │ 麦克风 Web Audio │ 扬声器/TTS 播放     │
│  聊天界面 │ KaTeX 公式 │ 图表渲染 │ 截图/屏幕共享             │
└──────────────────────┬───────────────────────────────────────┘
                       │ WebSocket / HTTP（localhost）
┌──────────────────────▼────────── Python 后端 ─────────────────┐
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Agent 编排：对话状态机、阅读进度、提示词工程               │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ 多模态管道：ASR → LLM（Qwen-VL/DeepSeek）→ TTS           │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ 书籍知识库：PDF 解析 → 分块 → 向量检索（RAG）              │  │
│  ├─────────────────────────────────────────────────────────┤  │
│  │ MCP Client：代码执行 / Anki / Obsidian / 搜索            │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

**为什么是这个架构？**
- 浏览器统一解决摄像头、麦克风、扬声器，零平台代码
- Python 是 AI 编排和 MCP 生态的最短路径
- MCP 可插拔：社区可贡献新的学习工具

---

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/yourname/book-buddy.git
cd book-buddy

# 后端
cd backend
pip install -r requirements.txt
python main.py

# 前端（新终端）
cd ../frontend
npm install
npm run dev

# 打开浏览器
open http://localhost:5173
```

> ⚠️ 项目尚在早期开发中，上述命令为预期用法，暂未实现。

---

## 技术栈

- **后端**：Python 3.11+, FastAPI, LangChain/LlamaIndex, Qwen-VL/DeepSeek API
- **前端**：Vue 3 / React + Vite（待定）
- **语音**：Qwen-Audio / 阿里云 ASR + TTS（流式）
- **向量库**：Chroma / sqlite-vec
- **MCP**：Anki MCP, Obsidian MCP, 代码执行 MCP

---

## MCP 工具集成（规划）

| 工具 | 用途 |
|---|---|
| 代码执行 | 概率模拟、数值验证、可视化 |
| Anki | 学完自动生成抽认卡 |
| Obsidian | 讲解沉淀为笔记，按章节归档 |
| 搜索 | 补充书中未讲的背景知识 |

> 本项目的工具能力全部通过 MCP 接入，社区可即插即用。

---

## 路线图

### v0.1（里程碑 1）—— 最小可用闭环
- [ ] 摄像头拍照 + 手动上传书页
- [ ] 书籍 PDF 解析与 RAG 知识库
- [ ] 语音输入（ASR）+ 文字输出
- [ ] 端到端验证：拍一页 → 问 → 答（带书籍上下文）

### v0.2
- [ ] 实时语音对话（流式 ASR + TTS）
- [ ] 当前页自动定位（视觉模型）

### v0.3
- [ ] MCP 代码执行（概率模拟）
- [ ] Anki 卡片自动生成

### v0.4+
- [ ] Obsidian 笔记沉淀
- [ ] 多书管理、阅读进度追踪

---

## 贡献

欢迎 Issue 和 PR！本项目采用 [MIT License](LICENSE)。

---

## 致谢

- [openai-realtime-console](https://github.com/openai/openai-realtime-console) — 音视频实时链路参考
- [textbook-to-note](https://github.com/drpwchen/textbook-to-note) — 教材解析思路
- [anki-mcp-server](https://github.com/ankimcp/anki-mcp-server) — Anki MCP 实现