FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY model/ ./model/
COPY static/ ./static/

RUN mkdir -p /app/backend/data

EXPOSE 8000

WORKDIR /app/backend
CMD ["python", "main.py"]
