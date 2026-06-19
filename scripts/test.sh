#!/usr/bin/env bash
# 运行后端测试套件
set -euo pipefail
cd "$(dirname "$0")/../backend"

echo "🧪 安装依赖（含 dev）…"
uv pip install --system -e ".[dev]" >/dev/null 2>&1 || uv sync --extra dev

echo "🧪 运行 pytest…"
uv run pytest -v --tb=short

echo "✅ 测试完成"
