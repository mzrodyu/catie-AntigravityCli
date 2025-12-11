FROM python:3.11-slim

WORKDIR /app

# 安装 Node.js
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 复制后端
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# 复制并构建前端
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build && rm -rf node_modules

# 环境变量
ENV HOST=0.0.0.0
ENV PORT=5002

EXPOSE 5002

CMD ["python", "main.py"]
