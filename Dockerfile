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

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/docs')" || exit 1

# 启动服务 (PORT 由 Python 读取环境变量)
WORKDIR /app/backend
CMD ["sh", "-c", "echo PORT=$PORT && python main.py"]
