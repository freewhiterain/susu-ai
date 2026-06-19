#!/usr/bin/env bash
# 一键启动小苏全部服务（Docker Compose）
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "⚠️  未找到 .env，正在从 .env.example 复制…"
  cp .env.example .env
  echo "👉 请编辑 .env 填入 OPENAI_API_KEY 等配置后重新运行。"
  exit 1
fi

echo "🚀 构建并启动服务…"
docker compose up -d --build

echo ""
echo "✅ 启动完成！"
echo "   前端管理后台: http://localhost:3000"
echo "   后端 API 文档: http://localhost:8000/docs"
echo "   Mock 内部 API: http://localhost:8001"
echo ""
echo "📥 首次使用请灌入知识库种子数据: ./scripts/seed.sh"
