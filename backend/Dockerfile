# 小苏后端镜像（使用 uv 管理依赖）
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 系统依赖（部分 wheel 需要编译工具）
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 引入 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 拷贝全部源码后安装（hatchling 需要 app 包存在才能构建本项目）
COPY . .
RUN uv pip install --system .

# 数据 / 日志目录（向量库与 SQLite 持久化挂载点）
RUN mkdir -p data logs data/chroma

EXPOSE 8000

# 生产用 uvicorn 多 worker 时需注意 Chroma 单进程；此处单进程 + 异步并发已足够
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
