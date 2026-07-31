# 第三轮变更审阅：语音链路（ASR + TTS + 流式朗读）

> **文档目的**：记录对「其他智能体语音链路产出」的审阅结论与改进建议，保持文档连续性，供下一个接手者参考。
>
> **审阅范围**：工作区中未提交的改动（8 个修改文件 + 3 个新增文件），将语音服务从占位实现推进到生产可用。
>
> **文档日期**：2026-07-31
> **最终验证**：后端 30 测试全过（22 → 30，新增 8 个语音测试），前端类型检查通过。

---

## 1. 审阅对象概述

本轮产出实现了完整的语音输入输出闭环，是项目路线图里「手不离书、动口提问」刚需的落地。

| 层 | 新增/修改 | 核心内容 |
|---|---|---|
| 后端·语音服务 | `backend/app/services/voice.py` | ASR（`qwen3-asr-flash`）+ TTS（`cosyvoice-v2`），真实 DashScope API |
| 后端·配置 | `config.py` / `models/config.py` / `routers/config.py` | 语音 key 独立于 LLM provider，`PUT /config` 支持 `voice_api_key` |
| 后端·测试 | `backend/tests/test_voice.py`（新增） | 8 个用例：转写、错误、空输入、key 校验、TTS 成败、配置解耦 |
| 前端·录音 | `frontend/src/utils/audio.ts`（新增） | getUserMedia + Web Audio，重采样 16kHz 单声道，手写 WAV 编码 |
| 前端·朗读 | `frontend/src/utils/tts.ts`（新增） | 按句切分流式朗读管线，首句即播 |
| 前端·集成 | `ChatInterface.vue` / `SettingsPanel.vue` / `api/client.ts` | 麦克风按钮、扬声器开关、设置面板语音 key 字段 |

**规模**：11 文件，覆盖前后端全链路。

---

## 2. 总体评价：优秀，可合并

实现质量超出预期。没有发现需要立即修复的阻塞性问题，三个改进点均为优化项。

### 亮点（值得后续保持的设计）

| 亮点 | 说明 | 价值 |
|---|---|---|
| **流式朗读管线** ⭐ | `SentenceStreamer` 按句切分 LLM 流式输出，首句一出现就 TTS 播放，不等整段生成完 | 感知延迟 ≈ 首句 TTS 时间，正是项目强调的目标 |
| **前端录音自力更生** | 不用 MediaRecorder 的 webm，而是 Web Audio 重采样 + 手写 WAV 编码 | 兼容性最稳，后端 ASR 直接吃 WAV，无需转码 |
| **优雅降级** | 未配 DashScope key 时自动回退浏览器 `speechSynthesis` + `webkitSpeechRecognition` | 零配置也能用语音，降低上手门槛 |
| **配置解耦** | 语音 key 独立于 LLM provider，`voice_api_key` 不动 provider | 支持「智谱 GLM 看图 + 通义千问语音」组合 |
| **公式朗读处理** | `spokenText()` 把 `$...$` → "公式"、代码块 → "代码片段" | 避免 TTS 朗读 LaTeX 源码 |
| **废弃 API 的合理取舍** | `createScriptProcessor` 已废弃但兼容性最好，作者注释说明了权衡 | 对短录音场景正确，不过度设计 AudioWorklet |

### 与上一轮修复的兼容性

| 上一轮改动 | 是否兼容 |
|---|---|
| `mask_key` 只露后 4 位 | ✅ 语音 key 也走 `mask_key`，测试断言 `***1234` 通过 |
| `renderRichText` 公式渲染 | ✅ `spokenText` 配合良好：渲染归渲染、朗读归朗读 |
| `VectorStore.invalidate()` | ✅ 未触及，无冲突 |
| Pydantic ConfigDict | ✅ 语音配置字段正确加入 |

**上轮没有一处被破坏。**

---

## 3. 验证结果

| 验证项 | 结果 |
|---|---|
| 后端测试 `pytest tests/` | **30 passed**（原 22 + 新增 8），1 个无关警告 |
| 前端类型检查 `vue-tsc --noEmit` | 通过 |
| 配置解耦测试 | `test_config_put_voice_key_keeps_provider` 通过——provider 不变、voice key 热生效 |
| ASR 临时文件清理 | 测试断言文件用完即删，通过 |

---

## 4. 发现的问题与改进建议

> 本轮**无阻塞性问题**。以下均为优化项，按优先级排列。

### 🟡 建议 1：TTS 串行播放可预取下一句（中优先级）

**位置**：`frontend/src/utils/tts.ts:89` 的 `TTSPlayer.pump()`

**现状**：朗读队列严格串行——等前一句播完才播下一句。合成（入队）与播放（消费）已分离，但播放间隙仍需等 `Audio.play()`。

**影响**：长回答时，若某句 TTS 合成慢（首句冷启动 1-2 秒），后续已合成好的音频也得排队，产生"卡顿感"。当前个人单对话场景感知不明显。

**建议**：在 `playAudio` 前预取下一句的 `Audio` 对象并调用 `.load()`，减少播放间隙。

```ts
// 伪代码示意：合成入队时即可创建 Audio 对象预热
enqueue(sentence: string): void {
  // ...
  this.queue.push(
    synthesizeVoice(text).then(b64 => {
      const audio = new Audio(`data:audio/mpeg;base64,${b64}`)
      audio.preload = 'auto'
      return audio  // 直接返回 Audio 对象而非 base64
    }).catch(() => null)
  )
}
```

**优先级**：中。当前可用，待真实使用反馈延迟后再决定是否优化。

---

### 🟡 建议 2：`apply_to_settings` mapping 补全语音字段（中优先级）

**位置**：`backend/app/services/config_store.py` 的 `apply_to_settings()`

**现状**：mapping 只含 LLM 字段。语音 key 走 `DASHSCOPE_API_KEY`（已在 mapping），热更新能生效——**当前不是 bug**。

**风险**：若未来语音配置独立成 `VOICE_API_KEY`（与 LLM 的 `DASHSCOPE_API_KEY` 分离），此处会漏掉热更新，导致改了配置但不生效的隐蔽问题。

**建议**：现在无需改动，但当引入独立语音 key 时，记得同步更新 mapping：

```python
# 未来扩展时的提醒（当前不需要）
mapping = {
    "LLM_PROVIDER": "llm_provider",
    "OPENAI_API_KEY": "openai_api_key",
    # ...
    # "VOICE_API_KEY": "voice_api_key",  # 引入独立语音 key 时加这行
}
```

**优先级**：中（前瞻性提醒）。

---

### 🟢 建议 3：消除 Starlette testclient 弃用警告（低优先级）

**位置**：测试输出中的 `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2`

**现状**：`test_config_put_voice_key_keeps_provider` 用 `TestClient` 触发了弃用警告，不影响功能，但测试日志有噪音。

**建议**：二选一：
- `pip install httpx2`（推荐）
- 或测试改用 `httpx.AsyncClient` 直连 ASGI app

**优先级**：低。纯卫生改进。

---

### 🟢 建议 4：录音超时与异常恢复（低优先级）

**位置**：`frontend/src/utils/audio.ts`

**现状**：录音依赖用户再次点击麦克风结束，没有最大时长保护。若用户录音后忘记停止、或浏览器异常导致 `onaudioprocess` 停止触发，录音器会"挂住"。

**建议**：
- 加最大录音时长（如 60 秒）自动停止
- `onaudioprocess` 加心跳检测，长时间无数据则报错

**优先级**：低。正常使用不易触发。

---

## 5. 给下一个智能体/开发者的建议

1. **语音已可用，优先验证真实体验**：建议配置 DashScope key 后实地测试一次完整链路（录音 → ASR → LLM → 流式 TTS 朗读），确认延迟与音质符合预期，再决定是否做建议 1 的预取优化。

2. **MCP 是下一个里程碑的核心**：语音补齐后，路线图里「学完自动沉淀 Anki 卡片」「概率模拟」需要 MCP 工具链。这是 README 已宣传的开源卖点，建议作为下一个重点。可参考 `ankimcp/anki-mcp-server`（~396 star）。

3. **若引入独立语音 key**：务必同步更新 `config_store.py` 的 mapping（见建议 2），否则会出现"改了配置不生效"的隐蔽 bug。

4. **前端录音用废弃 API 是有意为之**：`createScriptProcessor` 虽废弃但兼容性最好，对短录音场景正确。如未来要做长录音或实时音频处理，再迁移到 `AudioWorklet`，需单独 worklet 文件。不要轻易"现代化"这块。

5. **测试维护**：新增功能请保持当前测试风格——mock 掉真实网络调用，覆盖正常/错误/边界三条路径。本轮语音测试是良好范例。

6. **提交建议**：当前语音改动尚未提交，建议一个完整 commit：
   ```
   feat: 实装语音链路（ASR + TTS + 流式朗读）
   ```

---

## 6. 修改文件清单（本轮未提交）

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/app/services/voice.py` | 修改 | ASR/TTS 真实实现（DashScope） |
| `backend/app/config.py` | 修改 | 新增 `asr_model`/`tts_model`/`tts_voice` 字段 |
| `backend/app/models/config.py` | 修改 | `ConfigResponse`/`ConfigUpdate` 增语音字段 |
| `backend/app/routers/config.py` | 修改 | `voice_api_key` 独立更新逻辑 |
| `backend/tests/test_voice.py` | 新增 | 8 个语音测试 |
| `frontend/src/utils/audio.ts` | 新增 | WAV 录音器 |
| `frontend/src/utils/tts.ts` | 新增 | 流式朗读管线 |
| `frontend/src/components/ChatInterface.vue` | 修改 | 麦克风/扬声器 UI 与逻辑 |
| `frontend/src/components/SettingsPanel.vue` | 修改 | 语音 key 配置字段 |
| `frontend/src/api/client.ts` | 修改 | 语音/配置接口契约对齐 |
| `README.md` | 修改 | 文档更新 |

---

## 7. Git 提交链（审阅节点）

```
[未提交]  feat: 实装语音链路（ASR + TTS + 流式朗读）   ← 本轮审阅对象
0308351   docs: 新增第二轮变更审阅与修复记录
5825ae6   fix: 审阅修复 —— 安全加固、公式渲染、索引重建与配置现代化
6f0cc13   feat: 设置面板 —— 用户在界面自行配置 API Key
b36ed30   docs: 更新 README 技术栈与配置说明（智谱 GLM）
3f89d07   feat(backend): 切换到智谱 GLM-4.6V 与 embedding-3
3235b60   feat(frontend): 对齐后端接口契约，重设计界面
a299cf2   feat(backend): 实装 RAG 解析与 LLM 管道，修复接口契约
b649446   feat: 实现里程碑 1 核心功能
84415ff   feat: 初始化项目结构和文档
```

---

## 附：本项目文档索引

| 文档 | 内容 |
|---|---|
| `HANDOFF.md`（项目根） | 首轮：项目设计、架构选型、竞品调研、交接 |
| `docs/CHANGES_REVIEW_ROUND2.md` | 第二轮：RAG/LLM/配置面板的审阅与修复 |
| `docs/CHANGES_REVIEW_ROUND3.md` | 本文件：语音链路审阅与建议 |
