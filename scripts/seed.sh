#!/usr/bin/env bash
# 将 docs/ 下的知识库文档批量上传到后端，触发索引
set -euo pipefail
cd "$(dirname "$0")/.."

BACKEND="${BACKEND_URL:-http://localhost:8000}"
DOC_DIR="docs"

echo "📥 向 $BACKEND 灌入知识库种子文档…"

shopt -s nullglob
files=("$DOC_DIR"/*.md "$DOC_DIR"/*.txt "$DOC_DIR"/*.pdf "$DOC_DIR"/*.docx)

if [ ${#files[@]} -eq 0 ]; then
  echo "⚠️  $DOC_DIR 下没有可上传的文档"
  exit 0
fi

for f in "${files[@]}"; do
  echo "  → 上传 $(basename "$f")"
  curl -sf -X POST "$BACKEND/api/documents" \
    -F "file=@$f" >/dev/null && echo "    ✅ 已提交索引" || echo "    ❌ 失败"
done

echo ""
echo "✅ 种子文档已提交，索引在后台进行。可在管理后台「知识库」查看状态。"
