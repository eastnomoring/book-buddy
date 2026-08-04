# 多端迁移方案：微信小程序 + macOS / Windows / Linux

> **文档目的**：为 Book Buddy 从「纯 Web 前端」演进为「微信小程序 + 桌面三平台 + 保留 Web」提供可落地的迁移路线。
>
> **文档日期**：2026-08-03
> **现状基线**：Vue 3 + Vite 前端（`frontend/`），FastAPI 后端（`backend/`），SSE 流式对话、getUserMedia 拍照、Web Audio 录音、`Audio` 元素播放 TTS、marked + DOMPurify + KaTeX 渲染回答。

---

## 1. 目标与约束

**目标**

- 一套核心业务代码，覆盖四个端：微信小程序、macOS、Windows、Linux。
- Web 版不废弃（桌面端实际复用 Web 构建产物）。
- 后端 FastAPI 基本不变，只做部署形态与少量协议适配。

**硬约束（小程序平台限制，决定方案形状）**

| 限制 | 影响 |
|---|---|
| 小程序无 DOM/BOM | `marked`、`dompurify`、`katex` 全部不能直接用，回答渲染需换方案 |
| 无 `EventSource` | SSE 需改用 `wx.request({ enableChunked: true })`（基础库 ≥ 2.20.1） |
| 相机/麦克风走专有 API | `<camera>` 组件 + `RecorderManager`，不能用 `getUserMedia` / Web Audio |
| 网络请求域名白名单 | 后端必须部署到 **HTTPS + ICP 备案** 的域名，并在小程序后台配置 request 合法域名 |
| 主包体积 2MB（分包可至 20MB） | UI 框架与依赖要克制，KaTeX 字体这类资源不能进包 |
| 个人主体类目限制 | 「AI 问答」涉及深度合成服务，上架需资质评估，见 §8 风险 |

---

## 2. 技术选型

### 2.1 跨端 UI 框架：**uni-app（Vue 3）**

| 候选 | 结论 | 理由 |
|---|---|---|
| **uni-app（Vue 3 + Vite）** | ✅ 采用 | 现有前端是 Vue 3，组件/`script setup`/组合式 API 几乎平移；一套代码编译到微信小程序 + H5 + App |
| Taro 4 | 备选 | 同等能力，但 React 生态更顺，Vue 模式不如 uni-app 贴合现有代码 |
| 原生小程序重写 | 否 | 失去「一套代码」前提，H5/桌面端无法复用 |

### 2.2 桌面壳：**Tauri 2**

| 候选 | 结论 | 理由 |
|---|---|---|
| **Tauri 2** | ✅ 采用 | 直接加载 Web 版构建产物（`frontend/dist`），安装包 ~10MB，mac/win/linux 三平台签名打包成熟；Rust 壳可后续接本地能力（全局快捷键、本地摄像头权限更稳） |
| Electron | 备选 | 包体 ~150MB+，本项目无 Node 主进程需求，不值得 |
| 纯浏览器 | 兜底 | 桌面用户也可以直接用 Web 版，Tauri 只是体验增强 |

### 2.3 结论：一套后端 + 两个 UI 工程

```
┌─────────────────────────────────────────────┐
│ backend/ (FastAPI) —— 不动，仅加部署形态      │
└──────────────▲───────────────────▲──────────┘
               │ HTTPS/SSE         │ HTTPS/chunked
       ┌───────┴────────┐  ┌───────┴────────┐
       │ apps/web       │  │ apps/mp        │
       │ (现有 Vue3)     │  │ (uni-app →     │
       │                │  │  微信小程序)    │
       └───────▲────────┘  └───────▲────────┘
               │ dist             │
       ┌───────┴────────┐         │
       │ apps/desktop   │         │
       │ (Tauri 2 壳)   │         │
       └────────────────┘         │
       共享 packages/core ◀────────┘
       (类型 / API 客户端 / 平台适配接口)
```

---

## 3. 仓库结构调整（monorepo）

改用 pnpm workspace，根目录：

```
book-buddy/
├── backend/                  # 不变
├── packages/
│   └── core/                 # 跨端共享层（纯 TS，无 DOM 依赖）
│       ├── api/              # 后端接口定义 + 请求封装（平台无关）
│       ├── types/            # ChatMessage / BookInfo 等类型
│       └── platform/         # 平台适配接口定义（见 §5）
├── apps/
│   ├── web/                  # 现 frontend/ 整体迁入，依赖 packages/core
│   ├── mp/                   # uni-app 工程（微信小程序）
│   └── desktop/              # Tauri 2 壳，加载 apps/web 的 dist
├── docs/
└── pnpm-workspace.yaml
```

**共享层抽取原则**：`packages/core` 里只允许出现「平台无关」逻辑——类型、接口路径、请求参数组装、流式解析协议。凡是碰到 `window`/`document`/`wx`/`navigator` 的代码，一律下沉到各端自己的 adapter 实现里。

现有可直接平移进 core 的资产：`frontend/src/api/client.ts` 的请求参数/类型部分、`utils/tts.ts` 的 SentenceStreamer（按句切分是纯字符串逻辑）。

---

## 4. 后端改造点（很小）

| # | 改动 | 说明 |
|---|---|---|
| 1 | HTTPS + 域名部署 | 小程序强制 HTTPS + ICP 备案域名。用 Caddy/Nginx 反代 8000 端口即可，FastAPI 代码不用动 |
| 2 | SSE 协议微调 | `/api/chat/stream` 目前每个 chunk 一个 `data:` 行；小程序 `enableChunked` 拿到的是原始字节流，前端自行按 `\n\n` 切分即可，后端无需改格式 |
| 3 | CORS 不再需要（小程序无同源策略） | 保留现有 CORS 配置给 Web/桌面端用 |
| 4 | 鉴权（可选，上架建议加） | 当前后端裸奔，局域网自用没问题；部署到公网给小程序用，建议加一个简单的 token 校验（环境变量配置，中间件 5 行） |
| 5 | 上传大小限制 | 小程序 `wx.uploadFile` 与 Web 的 multipart 一致，`/api/books/upload`、`/api/voice/transcribe` 不用改 |

桌面端如果继续「后端跑本地、前端连 localhost:8000」，则 1/4 可以不做——但小程序端 1 是硬门槛。

---

## 5. 平台适配层（核心工作量所在）

`packages/core/platform/` 定义四个接口，各端分别实现：

| 接口 | Web / 桌面（Tauri） | 微信小程序 |
|---|---|---|
| `chatStream()` | `fetch` + `getReader()`（现状，`client.ts:131`） | `wx.request({ enableChunked: true })`，`onChunkReceived` 回调里做 UTF-8 增量解码 + `\n\n` 切帧 |
| `capturePhoto()` | `getUserMedia` 预览 + canvas 截帧（现状，`CameraCapture.vue:26`） | `<camera>` 组件 + `wx.createCameraContext().takePhoto`，返回临时文件路径转 base64 |
| `recordAudio()` | Web Audio 采集 PCM → WAV（现状，`utils/audio.ts`） | `RecorderManager`（格式选 PCM 或 MP3），结束得临时文件，`wx.uploadFile` 传 `/api/voice/transcribe` |
| `playAudio()` | `new Audio(data:audio/mpeg;base64,...)`（现状，`utils/tts.ts:107`） | `wx.createInnerAudioContext()`，`src` 写 base64 data URI 或先落临时文件 |

**渲染层差异（最大的坑）**：

- Web 端：`marked` → `dompurify` → `v-html` + KaTeX（现状 `utils/render.ts`），保留。
- 小程序端：无 DOM，改用 `<rich-text nodes>` 渲染 markdown 转出的节点树（可用 `mp-html` 组件，对表格/代码块支持好）。
- **数学公式**：KaTeX 依赖 DOM 测量，小程序不可用。三个选项按推荐排序：
  1. **服务端渲染**：后端加 `/api/render/formula`，用 matplotlib/mathtext 把 LaTeX 渲成 SVG/PNG，小程序 `<image>` 展示。一次实现全端受益，Web 端也可切换。
  2. 小程序端退化为「纯文本 LaTeX 源码 + 等宽字体」展示，体验打折但零成本，可作过渡期方案。
  3. `web-view` 嵌 H5 页面渲公式——需要业务域名备案且仅限企业主体，不推荐。

---

## 6. 组件迁移映射

| 现有（Web） | uni-app 小程序 | 改造量 |
|---|---|---|
| `App.vue` 两栏布局 | `pages/index/index.vue`，改上下结构（拍照区可折叠） | 小，样式重写为主 |
| `ChatInterface.vue`（581 行） | 对话页主体：气泡、`composer` 平移；录音/播放/SSE 换 adapter；`v-html` 换 `rich-text` | **大**，逻辑可留 70% |
| `CameraCapture.vue` | `<camera>` 组件重写预览与拍照 | 中，UI 重写 |
| `BookSelector.vue` | 平移，`input[type=file]` 换 `wx.chooseMessageFile`（会话文件）或相册 | 中 |
| `SettingsPanel.vue` | 平移为设置页/弹层，存储换 `uni.setStorageSync` | 小 |
| `utils/tts.ts` SentenceStreamer | 原样进 `packages/core` | 零 |
| `api/client.ts` | 拆：类型/参数进 core，传输层各端实现 | 中 |

UI 组件库建议用 **uv-ui / wot-design-uni**（uni-app Vue3 生态里维护活跃的），按钮、弹层、表单直接用，能省掉小程序端约一半的样式重写；配色 token 从 `style.css` 抄过去保持一致。

---

## 7. 分阶段实施计划

| 阶段 | 内容 | 验收标准 | 估算 |
|---|---|---|---|
| **P0 地基** | 后端部署到 HTTPS 备案域名；仓库改 monorepo；抽 `packages/core`（类型 + API 契约 + SentenceStreamer）；Web 端改为引用 core | Web 端功能回归不变，30 个后端测试全过 | 2~3 天（不含备案，备案需 2~4 周提前启动）（monorepo 与 core 抽取已完成于 2026-08-03，部署待办） |
| **P1 小程序骨架** | uni-app 工程初始化；对话链路打通：文本提问 → chunked 流式 → `rich-text` 展示（公式先按方案 2 纯文本过渡） | 真机上完成一次完整问答 | 3~4 天（工程与对话链路已完成于 2026-08-03，真机验证待办） |
| **P2 小程序能力补全** | 相机拍照、录音 ASR、TTS 播放、书籍选择/上传、设置页 | 真机功能对齐 Web 版 | 4~5 天（功能实现已完成于 2026-08-03，真机对齐验证待办） |
| **P3 桌面端** | Tauri 2 壳接入 Web dist；三平台打包（mac dmg / win msi / linux AppImage）；窗口尺寸、图标、自动更新（可选） | 三平台安装包可用 | 2~3 天（macOS 壳已完成于 2026-08-03：`Book Buddy.app` 与 dmg 已产出，回归通过；win/linux CI 打包与签名公证待办） |
| **P4 公式渲染 + 打磨** | 服务端公式渲染接口；小程序视觉对齐 Web 版设计令牌；分包优化 | 公式四端一致展示 | 2~3 天（服务端接口已由 Zcode 完成，小程序端接入完成于 2026-08-03；视觉对齐与分包优化待办） |

总计约 **13~18 个工作日**（不含备案等待）。P0 的备案和 P1 可以并行启动。

---

## 8. 风险与注意事项

1. **备案是关键路径**：域名 ICP 备案通常 2~4 周，决定小程序上线时间，第一天就要启动。
2. **上架资质**：AI 生成内容类小程序需按《深度合成管理规定》评估，个人主体大概率过不了「AI 问答」类目；如果上架是目标，提前确认主体资质。仅自用可走「体验版/开发版」不发布。
3. **chunked 流式稳定性**：`enableChunked` 在部分 Android 机型 + 经过 CDN 时可能被缓冲，P1 阶段要真机验证；兜底方案是退化为非流式 `/api/chat`。
4. **TTS base64 data URI 长度**：`InnerAudioContext` 对超长 data URI 不稳定，长句走「写临时文件再播」路径（`playAudio` adapter 里处理）。
5. **包体积**：主包只放对话页；书籍管理、设置放分包；不引入 KaTeX/字体文件。
6. **桌面端摄像头权限**：Tauri 的 webview 里 `getUserMedia` 在 macOS 需配置 `Info.plist` 的 `NSCameraUsageDescription`/`NSMicrophoneUsageDescription`，P3 注意。

---

## 9. 不做什么

- 不做原生 App（uni-app 的 App 端顺手可得，但不在本期验收范围）。
- 不重写后端，不换数据库，不动 RAG 管道。
- 桌面端不做 Electron，不做自绘 UI，保持「Web 构建产物 + 薄壳」。
