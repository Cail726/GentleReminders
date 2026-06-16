#!/bin/sh
echo "[GR-START] PORT env is: ${PORT:-NOT-SET}"
cd /app/backend
exec python main.py
