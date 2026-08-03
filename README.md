# Book Buddy

AI 伴读系统 —— 面向自学者读硬书的智能学习伴侣。

## 功能

- 📷 摄像头拍书页，自动识别当前页
- 🎙️ 语音提问，"手不离书"直接追问
- 📖 书籍知识库（RAG），用书中的符号体系回答
- 🧪 MCP 代码执行：概率模拟、可视化验证
- 🗂️ 自动生成 Anki 卡片 + Obsidian 笔记

## 快速开始

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的智谱 API Key（https://open.bigmodel.cn/ 创建）
# 默认使用 GLM-4.6V（多模态）+ embedding-3（向量嵌入）
# 也可以跳过本步，启动后在网页右上角 ⚙ 设置里直接填写

# 启动服务
python main.py
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173

### 语音功能（可选）

语音识别（ASR）与朗读（TTS）使用阿里云百炼 DashScope（qwen3-asr-flash + cosyvoice-v2）。
在网页右上角 ⚙ 设置的「语音服务」区域填入 DashScope Key（https://bailian.console.aliyun.com/ 创建）即可启用；
未配置时自动降级为浏览器自带的语音识别与朗读（Chrome/Edge 可用）。

## 技术栈

- 后端：Python, FastAPI, 智谱 GLM-4.6V（OpenAI 兼容接口，可换通义千问/硅基流动/Ollama）, Chroma
- 前端：Vue 3, TypeScript, Vite

## License

MIT