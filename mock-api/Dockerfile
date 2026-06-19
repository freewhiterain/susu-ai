# Mock 内部 API 服务
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
# Mock 服务是单文件应用，直接安装运行依赖即可（无需打包）
RUN uv pip install --system "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0"
COPY . .

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
