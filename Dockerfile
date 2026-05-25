# Gentle Reminders — Docker 部署
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY model/ ./model/
COPY static/ ./static/

# 创建数据目录 (与 database.py 中 DB_PATH 一致)
RUN mkdir -p /app/backend/data

# 暴露端口
EXPOSE 8000

# 启动服务
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
