# AntigravityCli

🚀 Antigravity Token 捐赠云端 - 共享 Antigravity Token，支持 Claude 4.5 / Gemini 3 Pro

## 功能特性

- ✅ Token 池共享 - 捐赠 Token 到公共池
- ✅ 额度奖励 - 捐赠获得额度
- ✅ OpenAI 兼容 API
- ✅ 支持 Claude / Gemini 模型
- ✅ 用户管理系统
- ✅ 精美 Web 界面

## 快速开始

### 1. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 2. 配置环境

```bash
cd backend
cp .env.example .env
# 编辑 .env 文件
```

### 3. 构建前端

```bash
cd frontend
npm run build
```

### 4. 启动服务

```bash
cd backend
python main.py
```

访问 http://localhost:5002

## API 使用

### Base URL
```
http://your-domain:5002/v1
```

### API Key
登录后在 Dashboard 复制

### 示例
```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="http://localhost:5002/v1"
)

response = client.chat.completions.create(
    model="claude-sonnet-4-5-20250514",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## 获取 Antigravity Token

1. 克隆 [antigravity2api-nodejs](https://github.com/liuw1535/antigravity2api-nodejs)
2. 运行 `npm run login` 获取 Token
3. 在 AntigravityCli 上传 Token

## Docker 部署

```bash
docker build -t antigravitycli .
docker run -d -p 5002:5002 antigravitycli
```

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy
- **前端**: React + TailwindCSS
- **数据库**: SQLite

## License

MIT
