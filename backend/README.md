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

创建 `.env` 文件：

```
DASHSCOPE_API_KEY=your_qwen_api_key
# 或
DEEPSEEK_API_KEY=your_deepseek_api_key
```

## 目录说明

- `app/routers/` - API 路由
- `app/services/` - 核心服务（LLM、RAG、语音、MCP）
- `app/models/` - 数据模型
- `data/` - 本地数据存储（PDF、向量库）