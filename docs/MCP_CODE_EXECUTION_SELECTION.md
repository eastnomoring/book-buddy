# MCP 代码执行接入 —— 选型记录（S4）

> **任务来源**：`docs/TASK_SPLIT_MULTI_PLATFORM.md` §7 S4
> **文档日期**：2026-08-04
> **状态**：选型已定，实现待做

---

## 1. 需求

伴学场景的杀手锏（HANDOFF §5）：用户问"大数定律是什么感觉？"，LLM 通过 function calling 调代码执行工具，模拟抛硬币 10 万次并画图，把抽象概念具象化。

GLM-4.6V 原生支持 Function Calling，后端 `/api/chat` 需实现 tool loop：
```
LLM 发起 function call → 后端执行 → 结果回注 → LLM 继续生成
```

## 2. 调研结论

### 2.1 MCP Python SDK

- 官方 [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)，~23.9k stars，成熟可用
- Client 通过 `stdio_client` 拉起 server 子进程，`ClientSession` 调 `list_tools()` / `call_tool(name, args)`
- Server 端用 `FastMCP` + `@mcp.tool()` 装饰器暴露工具

### 2.2 代码执行 server 候选

| 候选 | Stars | 沙箱机制 | 评价 |
|---|---|---|---|
| **philschmid/code-sandbox-mcp** | ~200 | Docker/Podman（llm-sandbox） | 最成熟，临时容器跑完即销毁 |
| JohanLi233/mcp-sandbox | ~40 | Docker 隔离 | 支持 install_package、API key 鉴权 |
| ~~pydantic/mcp-run-python~~ | — | Pyodide/WASM | **已归档**，隔离不稳、延迟高 |
| 官方 reference servers | 89.2k | — | **无代码执行 server** |

### 2.3 安全边界

| 隔离层级 | 安全性 | 复杂度 | 代表 |
|---|---|---|---|
| Docker 容器（临时、禁网络、资源 cap） | 高 | 中（需装 Docker） | philschmid |
| WASM/Pyodide | 中（有漏洞） | 低 | 已被 pydantic 放弃 |
| 裸子进程 + 超时 | 低 | 最低 | 不适合不可信代码 |

## 3. 选型决策

**采用自建受限执行器，而非引入第三方 MCP server。** 理由：

1. **本项目是个人学习工具**，执行的是 LLM 生成的概率模拟/数值验证代码，风险等级低，不是生产级不可信代码执行平台
2. **开箱即用优先**：强依赖 Docker 会显著增加开源项目的上手门槛（用户要先装 Docker + 拉镜像）
3. **MCP 协议化**：自建执行器以 MCP server 形式暴露（`@mcp.tool()`），保持"工具能力全靠 MCP 接入"的架构一致性，未来可平滑替换为 philschmid Docker 方案
4. **分层安全**：
   - **默认层（零依赖）**：受限子进程执行——`subprocess` + 超时（10s）+ 禁网络（`--network=none` 不可用于裸进程，改用 `socket.socket` patch）+ 内存限制（`resource.setrlimit`）+ 临时工作目录隔离
   - **增强层（可选）**：环境变量 `MCP_CODE_SANDBOX=docker` 时，切到 philschmid Docker 方案

### 安全措施清单（默认层）

| 措施 | 实现 |
|---|---|
| 超时 | `subprocess` 的 `timeout=10` 参数，超时杀进程 |
| 内存限制 | `resource.setrlimit(RLIMIT_AS, ...)` 限制 256MB |
| 网络隔离 | 执行脚本前置 `import socket; socket.socket = _block` |
| 文件系统隔离 | 临时目录（`tempfile.mkdtemp`）作为 cwd，执行后销毁 |
| 只允许 Python | 固定 `python3` 解释器，不接受其他命令 |
| 输出截断 | stdout/stderr 各截断到 4KB，防 OOM |
| 无持久状态 | 每次执行新子进程，不复用 |

## 4. 实现计划

1. **MCP server**：`backend/app/mcp/code_executor.py`——FastMCP server，暴露 `run_python` 工具
2. **MCP client 封装**：`backend/app/services/mcp_client.py`——拉起 server、list_tools、call_tool
3. **tool loop**：非流式 `/api/chat` 增加 function calling 循环（LLM → call_tool → 回注 → 继续）
4. **配置**：`MCP_CODE_ENABLED`（默认关，里程碑特性）、`MCP_CODE_SANDBOX`（local/docker）
5. **流式暂不支持 tool loop**（文档说明），因为流式中间插 tool call 会打断 SSE 流

## 5. 不做什么

- 不做流式 tool loop（复杂度高，首版非流式够用）
- 不做 Docker 增强层的实现（仅留接口和文档，按需启用）
- 不允许用户自定义工具（首版只有 run_python）
- 不执行非 Python 代码
