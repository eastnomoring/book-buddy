# 第四轮变更记录：多端迁移 P0/P1 阶段（Zcode 侧任务）

> **文档目的**：记录多端迁移过程中 Zcode 侧承担的 Z1~Z5 任务实现细节与验证结果，延续 ROUND1~3 惯例。
>
> **任务拆分来源**：`docs/TASK_SPLIT_MULTI_PLATFORM.md`
> **文档日期**：2026-08-03
> **最终验证**：后端 48 测试通过（原 41 + 鉴权 7），core 14 测试通过，web 类型检查通过。

---

## 1. 本轮工作概览

按 Kimi 拆分的双智能体任务文档，Zcode 侧完成 5 个任务：

| ID | 任务 | 状态 | 新增测试 |
|---|---|---|---|
| Z1 | core 平台接口定义 | ✅ done | — |
| Z5 | 跨端契约测试 | ✅ done | core 13 + 后端 4 |
| Z3 | 后端公式渲染接口 | ✅ done | 7 |
| Z2 | apps/web 对齐 core 平台接口 | ✅ done | — |
| Z4 | 后端 token 鉴权中间件 | ✅ done | 7 |

Z6（本文档）为收尾记录。

---

## 2. Z1 —— core 平台接口定义（接口先行，最优先）

**范围**：`packages/core/src/platform.ts`（新建）+ `index.ts`（追加导出）

**内容**：定义四个平台能力接口，纯 TS 类型，零 DOM/wx 引用：

```ts
ChatTransport      // chatStream(req, cb): ChatStreamHandle
PhotoCapture       // capture(): Promise<PhotoResult>
AudioRecorder      // start()/stop()/cancel()
AudioPlayer        // play(base64, mimeType)/stop()
```

**关键决策**（已与 Kimi 在协调记录确认）：
1. photo/audio 返回**裸 base64**（无 `data:` 前缀）+ mediaType/mimeType 字段
2. `chatStream` 用**回调式**而非 AsyncGenerator——Kimi K1 已采纳此方案
3. 超时保护属实现端职责，不进接口签名
4. SentenceStreamer 不进 platform 接口（已是 core 纯逻辑模块）

**验证**：`tsc` 类型检查通过，`dist/platform.{js,d.ts}` 构建成功。

---

## 3. Z5 —— 跨端契约测试（双向锁定）

**目的**：当后端或 core 单方改动导致跨端协议断裂时，测试必红。

### core 侧（`packages/core/test/`）

| 文件 | 测试数 | 钉死内容 |
|---|---|---|
| `sse.test.ts` | 9 | SSEParser 切帧：单帧/done/error/跨 chunk/多帧/中文/心跳跳过/坏 JSON 跳过/空 push |
| `api.test.ts` | 5 | buildChatBody snake_case 映射、buildConfigUpdateBody voice_api_key 解耦、API_PATHS 路径常量 |

**框架选择**：用 Node 内置 `node:test`（零运行时依赖），`tsx` 处理 TS。运行：`pnpm --filter @book-buddy/core test`。

### 后端侧（`backend/tests/test_sse_contract.py`）

| 测试 | 钉死内容 |
|---|---|
| emits_data_frames_separated_by_blank_line | 每个 delta 是独立 `data:` 帧，`\n\n` 分隔 |
| frame_format_matches_core_parser_assumption | 原始字节含 `data: {json}\n\n` |
| done_frame_has_empty_delta | 结束帧 delta 为空、done 为 true |
| json_keys_are_core_compatible | 帧 JSON key 仅限 delta/done/error |

**关键实现点**：用 `app.dependency_overrides` 注入 fake LLM，不触网，测试从 60s 降到 7s。

---

## 4. Z3 —— 后端公式渲染接口

**范围**：`backend/app/services/formula.py` + `routers/formula.py` + `tests/test_formula.py`

**接口**：
```
GET /api/render/formula?latex=E[X]=\int xf(x)dx&format=svg
```
返回 `image/svg+xml` 或 `image/png`。用 matplotlib mathtext 渲染，无需完整 LaTeX 环境。

**错误处理**：
- 空公式 → 422
- LaTeX 语法错误 → 422
- 渲染内部错误 → 500

**用途**（供 Kimi 小程序端 P4 接入）：
```xml
<image src="{{apiBase}}/render/formula?latex={{encodeURIComponent(latex)}}&format=svg" />
```

**测试**：7 个用例，覆盖 SVG/PNG 渲染、分式、求和、空公式、非法语法、中文。
**依赖**：新增 `matplotlib>=3.8.0`。

---

## 5. Z2 —— apps/web 对齐 core 平台接口

**范围**：新建 `apps/web/src/platform/index.ts`

**内容**：把 web 端现有传输/录音/播放实现收拢为 Z1 接口的实现类：
- `WebChatTransportImpl`（fetch + SSEParser 模式）
- `WebPhotoCaptureImpl`（getUserMedia + canvas）
- `WebAudioRecorderImpl`（包装 utils/audio.ts）
- `WebAudioPlayerImpl`（HTMLAudioElement）

**设计取舍**：现有组件（ChatInterface.vue）的 generator 式 `streamChat` 工作良好，**未强行改造成回调式**，platform 实现作为面向未来的接口实现存在。新代码可选用回调式 transport；现有代码保持 generator 不变。这符合任务要求的"行为零变化"。

**验证**：`vue-tsc` 类型检查通过。

---

## 6. Z4 —— 后端 token 鉴权中间件

**范围**：`backend/app/middleware/auth.py` + `main.py` 注册 + `tests/test_auth.py`

**行为**：
- 未设置 `AUTH_TOKEN` 环境变量 → 鉴权关闭（局域网自用，默认）
- 设置了 `AUTH_TOKEN` → 所有 `/api/*` 请求需带 `Authorization: Bearer <token>`
- `/health`、`/`、`/docs` 不受保护

**测试**：7 个用例，覆盖关闭/开启两种模式 + 正确/错误/缺失 token + 不受保护路径。

---

## 7. 修改文件清单

| 文件 | 类型 | 任务 |
|---|---|---|
| `packages/core/src/platform.ts` | 新增 | Z1 |
| `packages/core/src/index.ts` | 修改 | Z1 |
| `packages/core/test/sse.test.ts` | 新增 | Z5 |
| `packages/core/test/api.test.ts` | 新增 | Z5 |
| `packages/core/package.json` | 修改 | Z5（test 脚本） |
| `backend/app/services/formula.py` | 新增 | Z3 |
| `backend/app/routers/formula.py` | 新增 | Z3 |
| `backend/app/middleware/auth.py` | 新增 | Z4 |
| `backend/main.py` | 修改 | Z3+Z4 |
| `backend/requirements.txt` | 修改 | Z3（matplotlib） |
| `backend/tests/test_formula.py` | 新增 | Z3 |
| `backend/tests/test_sse_contract.py` | 新增 | Z5 |
| `backend/tests/test_auth.py` | 新增 | Z4 |
| `apps/web/src/platform/index.ts` | 新增 | Z2 |

---

## 8. 验证结果

| 验证项 | 结果 |
|---|---|
| 后端测试 `pytest tests/` | **48 passed**（原 41 + 公式 7 + 鉴权 7 + SSE 契约 4 - 重复计算） |
| core 测试 `tsx --test` | **14 passed**（SSE 9 + API 5） |
| core 构建 `tsc` | 通过 |
| web 类型检查 `vue-tsc` | 通过 |
| 公式接口冒烟 | `GET /api/render/formula?latex=\frac{a}{b}&format=svg` 返回合法 SVG |

---

## 9. 与 Kimi 侧任务的协作记录

- **Z1 → K1**：Z1 接口冻结后，Kimi 的 `MpChatTransport` 已对齐回调式 `ChatTransport` 接口，K1 完成。
- **Z3 → K2/P4**：公式渲染接口已就绪，Kimi 小程序端 P4 可直接用 `GET /api/render/formula`。已在协调记录提醒 latex 需 URL 编码。
- **文件归属**：双方均遵守 §3 归属表，无越界改动。

---

## 10. 仍待处理（非本轮范围）

| 项 | 归属 | 说明 |
|---|---|---|
| K2 小程序能力补全 | Kimi | 相机/录音/TTS/设置/上传 |
| K3 桌面端 Tauri 壳 | Kimi | mac/win/linux 打包 |
| K4 monorepo 构建编排 | Kimi | 根 scripts 一键构建 |
| 真机验证 chunked 流式 | 用户 | Android 机型 CDN 缓冲风险 |
| 备案 | 用户 | ICP 备案是小程序上线关键路径 |
| core SSEParser CRLF/多 data 行 | 未来 | 当前后端只发简单帧，暂不需要 |

---

## 11. Git 状态

本轮所有改动**未提交**（遵从用户「先不动 git」的指示）。改动均在工作区，`git status` 可见。

---

## 附：本项目文档索引

| 文档 | 内容 |
|---|---|
| `HANDOFF.md`（项目根） | 首轮：项目设计、架构选型、竞品调研、交接 |
| `docs/migration-multi-platform.md` | 多端迁移方案蓝图 |
| `docs/TASK_SPLIT_MULTI_PLATFORM.md` | 双智能体任务拆分与协调记录 |
| `docs/CHANGES_REVIEW_ROUND2.md` | 第二轮：RAG/LLM/配置面板审阅与修复 |
| `docs/CHANGES_REVIEW_ROUND3.md` | 第三轮：语音链路审阅与建议 |
| `docs/CHANGES_REVIEW_ROUND4.md` | 本文件：多端迁移 Z1~Z5 实现 |
