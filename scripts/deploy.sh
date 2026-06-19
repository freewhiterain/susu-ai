#!/usr/bin/env bash
# 生产部署脚本：拉取最新代码 → 重建镜像 → 滚动重启 → 健康检查
set -euo pipefail
cd "$(dirname "$0")/.."

echo "🔄 拉取最新代码…"
git pull --ff-only || echo "（跳过 git pull）"

if [ ! -f .env ]; then
  echo "❌ 缺少 .env，无法部署。请先配置生产环境变量。"
  exit 1
fi

echo "🏗️  重建镜像…"
docker compose build

echo "♻️  滚动重启…"
docker compose up -d

echo "⏳ 等待后端健康检查…"
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ 后端就绪"
    break
  fi
  sleep 2
  if [ "$i" -eq 30 ]; then
    echo "❌ 后端健康检查超时，请查看日志: docker compose logs backend"
    exit 1
  fi
done

echo "🧹 清理悬空镜像…"
docker image prune -f >/dev/null 2>&1 || true

echo "✅ 部署完成"
docker compose ps
