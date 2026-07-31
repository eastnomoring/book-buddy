# 变更审阅与修复记录（第二轮）

> **文档目的**：记录对「其他智能体产出」的审阅结论与具体修复，供下一个接手的智能体/开发者快速理解当前代码状态与演进脉络。
>
> **提交范围**：审阅 `84415ff`（本会话首轮基线）之后、由其他智能体提交的 5 个 commit（`b649446 → 6f0cc13`），并对发现的问题做出修复（本次提交 `5825ae6`）。
>
> **文档日期**：2026-07-31
> **最终验证**：后端 22 测试全过，前端类型检查通过，端到端冒烟通过。

---

## 1. 被审阅方的产出概述（其他智能体的 5 个 commit）

| Commit | 内容 |
|---|---|
| `a299cf2` | 实装 RAG 解析（PyMuPDF）与 LLM 管道，修复接口契约 |
| `3235b60` | 前端对齐后端契约，重设计界面 |
| `3f89d07` | 后端切换到智谱 GLM-4.6V 与 embedding-3 |
| `b36ed30` | 更新 README 技术栈与配置说明 |
| `6f0cc13` | 设置面板：界面自行配置 API Key |

**规模**：+4037 / -860 行，29 个文件。把我留下的占位实现全部变成可真实运行的系统，并补齐了「界面配置 API Key」这一关键缺口。

---

## 2. 总体评价

**质量优秀，可以合并。** 架构延续了我的 FastAPI + Vue 分层设计，没有无谓重构；RAG/LLM/配置三大块从占位推进到实装；测试覆盖扎实（18 个用例）。

发现 3 个必须修的问题（1 安全 + 2 工程）与 4 个建议项，已全部处理（其中 1 项经复查为误判、1 项对方已处理）。

---

## 3. 发现的问题与修复

### 🔴 修复 1：`mask_key` 泄露 API Key 可辨识前缀

**问题**：`backend/app/services/config_store.py` 的掩码函数同时暴露前 3 位和后 4 位。

```python
# 修复前 —— 共 7 个明文字符
return f"{key[:3]}***{key[-4:]}"   # a93e...skP4
```

智谱/通义千问的 Key 长达 32+ 位，配合公开的 base_url，前 3 位会显著缩小爆破空间。

**修复**：只保留后 4 位。

```python
# 修复后 —— 仅后 4 位
return f"***{key[-4:]}"            # ***skP4
```

**涉及文件**：
- `backend/app/services/config_store.py`
- `backend/tests/test_config_store.py`（用例同步更新）

**验证**：接口实测返回 `api_key_masked: "***skP4"`；6 个参数化用例覆盖 `None/空/4位/5位/长Key` 边界。

---

### 🔴 修复 2：前端公式不渲染（核心体验缺陷）

**问题**：`ChatInterface.vue` 用 `v-html` 渲染 LLM 回复，但自写的 markdown 渲染器只处理加粗/斜体/行内代码，**数学公式 `$...$` 与代码块 ` ``` ` 完全不渲染**。用户读的是《普林斯顿概率论》，公式是核心内容。

**修复**：新建独立渲染管线 `frontend/src/utils/render.ts`，三段式处理：

```
原始文本
  → extractMath：把 $...$ / $$...$$ 替换为 Unicode 私用区占位符
  → marked.parse：标准 Markdown → HTML
  → restoreMath：占位符还原为 KaTeX 渲染结果
  → DOMPurify.sanitize：清洗，杜绝 XSS
```

关键设计点：
- **占位预处理**：必须先抽出公式再交给 marked，否则 `$` 会被当字面量吞掉。
- **DOMPurify**：浏览器原生环境，不引 jsdom（避免污染构建）。`v-html` 由此变得安全。
- **兼容性**：避免 `String.replaceAll`（当前 tsconfig target 不支持），改用全局正则替换；私用区字符在正则里是字面量，安全。

**涉及文件**：
- `frontend/src/utils/render.ts`（新增）
- `frontend/src/components/ChatInterface.vue`（删除自写 `renderMarkdown`，改用 `renderRichText`）
- `frontend/src/main.ts`（全局引入 `katex/dist/katex.min.css`）
- `frontend/package.json`（新增 `katex` / `marked` / `dompurify` / `@types/dompurify`）

**验证**：`vue-tsc --noEmit` 通过；`.katex-display` 的横向溢出滚动样式在 `style.css` 中已存在。

---

### 🔴 修复 3：配置热更新依赖私有属性访问

**问题**：`config_store.py` 的 `apply_to_settings` 直接改私有属性来强制重建嵌入函数。

```python
# 修复前 —— 脆弱，VectorStore 重构会静默失效
rag_service.vector_store._initialized = False
```

**修复**：给 `VectorStore` 加公共方法 `invalidate()`，内部重置 `_initialized` 与 `collection`。

```python
def invalidate(self) -> None:
    """标记向量库为未初始化，下次访问时按当前配置惰性重建。"""
    self._initialized = False
    self.collection = None
```

调用处改为 `rag_service.vector_store.invalidate()`。

**涉及文件**：
- `backend/app/services/rag.py`（新增 `invalidate()`）
- `backend/app/services/config_store.py`（改调用）
- `backend/tests/test_rag_invalidate.py`（新增，覆盖 invalidate 与索引重建）

---

### 🟡 修复 4：Pydantic V2 deprecation 告警

**问题**：`config.py` 用了 V1 风格的 `class Config:` 内嵌类，Pydantic V2 会告警，V3 将移除。

**修复**：改用 `model_config = SettingsConfigDict(...)`。

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

**涉及文件**：`backend/app/config.py`
**验证**：测试输出中的 `PydanticDeprecatedSince20` 告警消失。

---

### 🟡 修复 5：重启后书籍索引丢失

**问题**：`books_db` 是进程内字典，PDF 已落盘、向量已持久化，但重启后内存索引为空，前端看不到已上传的书。

**修复**：
1. 上传时把 `BookInfo` 写成 sidecar `data/books/{book_id}.json`。
2. 新增 `rebuild_books_index()`：启动时扫描目录、载入所有 sidecar 重建内存索引；若 `total_pages<=0`（解析未完成就被重启），用向量库中该书的最大页码回填。
3. 在 `main.py` 的 `lifespan` 中调用。
4. 路径统一用 `BOOKS_DIR` 常量（替换原来的硬编码 `"./data/books"`），删除/解析处一并统一。

**涉及文件**：
- `backend/app/routers/book.py`（`_save_meta`/`_load_meta`/`rebuild_books_index`，上传/删除/解析逻辑统一）
- `backend/main.py`（lifespan 调用）
- `backend/tests/test_rag_invalidate.py`（新增重建测试）

**验证**：测试用临时目录模拟 sidecar 写入与重建，断言索引恢复正确。

---

### 🟡 修复 6（撤回）：voice 路由未注册

**说明**：首轮审阅时我误判「`voice.py` 路由未挂载」。复查 `backend/main.py:59` 发现 **它已正确注册**（`app.include_router(voice.router, prefix="/api", ...)`）。此项为审阅疏漏，已撤回，无需改动。

---

### 🟡 修复 7（无需改动）：langchain 冗余依赖

**说明**：首轮基线里 `requirements.txt` 列了 langchain，但实装的 RAG 直接用 PyMuPDF + Chroma。**其他智能体在 `3f89d07` 已将其移除**，当前 `requirements.txt` 已是 `pymupdf + chromadb`。无需改动。

---

## 4. 修改文件清单（本次提交 `5825ae6`）

| 文件 | 类型 | 说明 |
|---|---|---|
| `backend/app/config.py` | 修改 | Pydantic V2 ConfigDict |
| `backend/app/services/config_store.py` | 修改 | mask_key 加固 + 调用 invalidate |
| `backend/app/services/rag.py` | 修改 | 新增 VectorStore.invalidate() |
| `backend/app/routers/book.py` | 修改 | sidecar 持久化 + 索引重建 |
| `backend/main.py` | 修改 | lifespan 调用 rebuild |
| `backend/tests/test_config_store.py` | 修改 | mask_key 用例更新 |
| `backend/tests/test_rag_invalidate.py` | 新增 | invalidate + 重建测试 |
| `frontend/src/utils/render.ts` | 新增 | marked+KaTeX+DOMPurify 渲染管线 |
| `frontend/src/components/ChatInterface.vue` | 修改 | 改用 renderRichText |
| `frontend/src/main.ts` | 修改 | 引入 katex CSS |
| `frontend/package.json` / `package-lock.json` | 修改 | 新增前端依赖 |

**规模**：12 文件，+289 / -45 行。

---

## 5. 验证结果

| 验证项 | 结果 |
|---|---|
| 后端测试 `pytest tests/` | **22 passed**（原 18 + 新增 4），无告警 |
| 前端类型检查 `vue-tsc --noEmit` | 通过 |
| 后端启动 | 正常，lifespan 输出书籍恢复日志 |
| `GET /api/config` | 返回掩码 `***skP4`（修复1生效） |
| `GET /api/books` | 返回 `[]`（空库正常） |
| `GET /health` | 返回 `openai:glm-4.6v` |

---

## 6. 仍待处理（建议下一迭代，未阻塞）

| 优先级 | 事项 | 说明 |
|---|---|---|
| 中 | 上传 PDF 无大小限制 | `await file.read()` 全量读入，大文件可能撑爆内存；建议流式落盘 + 大小上限 |
| 中 | 语音链路仍是占位 | ASR/TTS 返回假数据；用户明确「语音是刚需」，应排进下一里程碑 |
| 低 | `cors_origins` 定义与使用分离 | config 定义了但 main 可直接读，统一即可 |
| 低 | MCP 集成 | 路线图里的代码执行/Anki/Obsidian 工具尚未接入 |
| 低 | `render.ts` 占位符用模块级变量 | `placeholders` 是模块级，并发渲染理论上会串；当前单用户单对话无实际影响，多用户场景需改为函数局部 |

---

## 7. 给下一个智能体的建议

1. **优先做语音**：用户多次强调「手不离书、动口提问」是核心体验，但目前整条语音链路是占位。建议接入通义千问 Qwen-Audio 或阿里云 ASR/TTS，流式链路。
2. **PDF 大小限制**与流式上传是低成本高收益的健壮性改进。
3. **MCP 是开源故事的核心卖点**（README 已宣传），建议尽早接一个最小工具（如代码执行）跑通「LLM 调工具」闭环。
4. 修改 `render.ts` 时注意：占位符机制依赖「先抽公式再 marked」，不要轻易调整顺序；若改为多用户，把 `placeholders` 移入函数作用域。
5. 提交信息建议继续遵循 Conventional Commits（本次为 `fix:`）。

---

## 附：Git 提交链

```
5825ae6  fix: 审阅修复 —— 安全加固、公式渲染、索引重建与配置现代化  ← 本次
6f0cc13  feat: 设置面板 —— 用户在界面自行配置 API Key
b36ed30  docs: 更新 README 技术栈与配置说明（智谱 GLM）
3f89d07  feat(backend): 切换到智谱 GLM-4.6V 与 embedding-3
3235b60  feat(frontend): 对齐后端接口契约，重设计界面
a299cf2  feat(backend): 实装 RAG 解析与 LLM 管道，修复接口契约
b649446  feat: 实现里程碑 1 核心功能                                  ← 本会话首轮基线
84415ff  feat: 初始化项目结构和文档
```
