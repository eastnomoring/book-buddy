# Book Buddy

AI 伴读系统 —— 面向自学者读硬书的智能学习伴侣。一套后端，四端可用：网页、macOS 桌面 App、微信小程序、（桌面壳复用网页版，Windows/Linux 打包待 CI）。

## 功能

- 📷 摄像头拍书页，带图提问
- 📍 **当前页定位**：拍照后自动识别你在读第几页/哪一章，回答优先用该章上下文
- 🎙️ 语音提问，"手不离书"直接追问；回答可语音朗读（按句流式）
- 📖 书籍知识库（RAG），用书中的符号体系回答
- 🧪 **MCP 代码执行**：问"大数定律是什么感觉？"→ 直接模拟抛硬币 10 万次并画图（受限沙箱，`.env` 设 `MCP_CODE_ENABLED=true`）
- 🃏 **Anki 卡片**：学完知识点可自动生成抽认卡（需本机 Anki + AnkiConnect，`.env` 设 `ANKI_ENABLED=true`）
- 📝 **本地笔记**：讲解可沉淀为 `data/notes/` 下按书/章节归档的 markdown（零依赖；Obsidian 可直接把该目录当 vault）
- √ 数学公式渲染：网页端 KaTeX，小程序端服务端渲染为图片
- 🗂️ 规划中：搜索 MCP（见 `docs/SEARCH_MCP_SELECTION.md`，本轮暂缓）

## 快速开始

### 0. 一次性准备

```bash
# 后端：虚拟环境 + 依赖
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 后端：环境变量（也可跳过，启动后在网页 ⚙ 设置里直接填 API Key）
cp .env.example .env
# 编辑 .env，填入智谱 API Key（https://open.bigmodel.cn/ 创建）
# 默认 GLM-4.6V（多模态）+ embedding-3（向量嵌入）

# 前端：monorepo 依赖（apps/web + apps/mp + packages/core）
cd ..
pnpm install
```

---

## 场景一：网页版（最简单，推荐先用这个）

```bash
pnpm start -- --build   # 首次：构建前端并启动
pnpm start              # 之后每次启动
```

一条命令拉起后端 + 静态托管前端，自动打开 http://localhost:5173 （`/api` 自动反代到 8000 端口）。

页面内操作：

- **上传书籍**：左侧书籍区域上传 PDF，等待解析入库
- **文字提问**：底部输入框直接问，回答流式输出、KaTeX 渲染公式
- **拍照提问**：点拍照按钮授权摄像头，拍书页随问题一起发送
- **语音**：麦克风按钮语音输入；回答自动朗读（可关闭）
- **设置（右上角 ⚙）**：填智谱 API Key、DashScope Key（语音服务）、切换模型

停止：终端里 Ctrl+C（会连带关闭后端）。

---

## 场景二：macOS 桌面 App

**开发模式**（改动即时生效）：

```bash
pnpm start:desktop    # 后端 + vite 热更新 + Tauri 壳，需 Rust 工具链
```

**打包成 .app / .dmg**（分发给其他 Mac）：

```bash
pnpm build:desktop
# 产物：
#   apps/desktop/src-tauri/target/release/bundle/macos/Book Buddy.app
#   apps/desktop/src-tauri/target/release/bundle/dmg/Book Buddy_0.1.0_x64.dmg
```

首次打开拍照/录音时 macOS 会弹摄像头、麦克风授权，允许即可（`Info.plist`/`Entitlements.plist` 已配置）。
桌面 App 内是网页版同一套界面。注意：**打包的 .app 不会自己启动后端**，需要先 `pnpm start`（或只起后端 `pnpm dev:backend`）；开发模式 `pnpm start:desktop` 则会自动连带拉起后端。

---

## 场景三：微信小程序

### 开发版（本机调试）

```bash
pnpm start           # 1. 先起后端（小程序要连它）
pnpm build           # 2. 构建小程序：apps/mp/dist/build/mp-weixin
```

3. 微信开发者工具 → 导入 `apps/mp/dist/build/mp-weixin`（AppID 选「测试号」即可）
4. **必须勾选**：详情 → 本地设置 →「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」
5. 点「编译」，即可完整使用：拍照、相册、录音提问、朗读、上传书籍、公式图片渲染

### 真机预览（手机扫码）

`localhost` 在手机上指手机自己，需要两步调整：

1. 后端绑到局域网：`cd backend && .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000`
2. 小程序内「设置」页把后端地址改为电脑局域网 IP，如 `http://192.168.1.5:8000/api`（必须带 `/api` 后缀；手机与电脑同一 Wi-Fi）

### 正式上线（以后）

需要 HTTPS + ICP 备案域名，并在小程序后台配置 request 合法域名，详见 `docs/migration-multi-platform.md`。

---

## 场景四：开发模式（改代码时用）

```bash
pnpm start:dev       # 后端 --reload + vite 热更新，一条命令全起
```

或分开起：

```bash
pnpm dev:backend     # 只起后端（uvicorn --reload，:8000）
pnpm dev:web         # 只起前端（vite，:5173，已配置 /api 代理）
pnpm dev:mp          # 小程序 watch 模式（开发者工具里同步刷新）
```

---

## 常用命令一览

| 命令 | 作用 |
|---|---|
| `pnpm start` | 一键启动（生产形态：后端 + 静态前端） |
| `pnpm start:dev` / `start:desktop` | 开发 / 桌面形态一键启动 |
| `pnpm build` | 构建 core → web → 小程序 |
| `pnpm build:desktop` | 构建并打包 macOS .app/.dmg |
| `pnpm test` | core 测试 + 后端 48 个 pytest |
| `pnpm dev:backend` / `dev:web` / `dev:mp` | 单独起某一端 |

`pnpm start` 的可选参数：`--build`（先构建）、`--port`（前端端口）、`--backend-port`、`--no-open`（不开浏览器）。

---

## 配置说明

| 配置 | 在哪填 | 用途 |
|---|---|---|
| 智谱 API Key | `backend/.env` 或网页 ⚙ 设置 | LLM + embedding，必填 |
| DashScope Key | 网页 ⚙ 设置「语音服务」 | ASR/TTS；未配置时网页端降级为浏览器自带语音，小程序端语音不可用 |
| `AUTH_TOKEN` | `backend/.env` | 可选鉴权：设置后除 `/health`、`/docs` 外都需带 token（部署到公网时建议开启） |
| `MCP_CODE_ENABLED` | `backend/.env` | 可选：设为 `true` 开启 MCP 代码执行（概率模拟/数值验证/画图），受限沙箱（超时 10s、禁网络、256MB 内存），默认关闭 |
| `ANKI_ENABLED` | `backend/.env` | 可选：设为 `true` 开启 Anki 抽认卡工具；需本机安装 Anki + AnkiConnect 插件（码 `2055492159`）并保持 Anki 运行 |
| `OPENAI_THINKING` | `backend/.env` | 可选：GLM 思考模式，讲解复杂证明时开（`true`），日常问答关（默认 `false` 降低首字延迟） |
| 小程序后端地址 | 小程序「设置」页 | 默认 `http://localhost:8000/api`，真机改局域网 IP |

**Anki 使用步骤**：① 安装桌面版 Anki → ② 插件「获取插件」输入 `2055492159` 安装 AnkiConnect → ③ 保持 Anki 开启 → ④ `.env` 设 `ANKI_ENABLED=true` 并重启后端。牌组默认 `Book Buddy`，卡片模型 `BookBuddy Card`（正面问题+出处，背面讲解）。选型详见 `docs/ANKI_MCP_SELECTION.md`。

**当前页定位行为**：拍照提问时后端会先做一次轻量视觉识别（约 1-2s），识别你读的页码/章节并收窄检索；识别失败自动降级为整书检索，不影响提问。

## 各端能力对照

| 能力 | 网页版 | macOS App | 微信小程序 |
|---|---|---|---|
| 文字 / 流式回答 | ✅ | ✅ | ✅（chunked 流式） |
| 拍照 / 相册 | ✅ | ✅ | ✅ |
| 语音输入 ASR | ✅（有浏览器兜底） | ✅ | ✅ |
| 语音朗读 TTS | ✅（有浏览器兜底） | ✅ | ✅（按句流式） |
| 书籍上传 / 切换 | ✅ | ✅ | ✅（会话文件 PDF） |
| 公式渲染 | KaTeX | KaTeX | 服务端渲染图片 |

## 技术栈

- 后端：Python, FastAPI, 智谱 GLM-4.6V（OpenAI 兼容接口，可换通义千问/硅基流动/Ollama）, Chroma
- 前端：Vue 3, TypeScript, Vite（`apps/web`）
- 小程序：uni-app Vue 3（`apps/mp`，与 web 共享 `packages/core`）
- 桌面：Tauri 2 壳加载 web 构建产物（`apps/desktop`）
- monorepo：pnpm workspace

## License

MIT
