# Book Buddy Backend

AI 伴读系统后端服务。

## 快速开始

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

## 环境变量

复制 `.env.example` 为 `.env` 并按注释填写（LLM/语音/RAG/鉴权等完整配置项见该文件）：

```bash
cp .env.example .env
```

注意：部署到非本机环境时务必设置 `AUTH_TOKEN`，否则所有 `/api/*` 接口完全开放。

## 目录说明

- `app/routers/` - API 路由
- `app/services/` - 核心服务（LLM、RAG、语音、MCP）
- `app/models/` - 数据模型
- `data/` - 本地数据存储（PDF、向量库）