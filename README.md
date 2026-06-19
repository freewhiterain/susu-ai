# 小苏 · 企业内部 AI 助手

> 面向公司全员的智能助手：基于内部知识库的检索增强问答（RAG），支持工具调用、流式输出、引用溯源、Token 成本核算，并接入钉钉 IM 与 Web 管理后台。

---

## ✨ 功能总览

| 模块 | 能力 |
| --- | --- |
| 📚 知识库 | 支持 Markdown / TXT / PDF / Word 上传，自动切片 + 向量化，同名文件增量更新 |
| 🤖 智能问答 | RAG 检索 + LLM 生成，**强制引用溯源**（【来源：xxx】），SSE 流式输出 |
| 🛠️ 工具调用 | 知识库检索、员工/考勤/订单查询、当前时间，最多 5 轮自动编排 |
| 💬 IM 接入 | 钉钉企业内部机器人（HMAC 验签、5s 内响应、会话隔离） |
| 🖥️ 管理后台 | 概览看板、知识库管理、对话日志（含 Token/成本）、系统设置 |
| 📊 可观测性 | Langfuse 链路追踪（可选）、结构化日志、对话落库 |
| 🔌 MCP Server | 将内部工具以 MCP 协议暴露给任意兼容客户端 |
| 🧪 评测 | 20 用例离线评测脚本，覆盖工具选择 / 引用合规 / 拒答边界 |

## 🏗️ 技术架构

```
┌──────────────┐    ┌─────────────────────────────────────────┐
│  Next.js 15  │    │              FastAPI Backend             │
│  管理后台/聊天 │───▶│  ┌────────┐  ┌──────────┐  ┌──────────┐  │
└──────────────┘ SSE│  │ Agent  │─▶│  Tools   │  │   RAG    │  │
                    │  │ 主循环  │  │ Registry │  │ Pipeline │  │
┌──────────────┐    │  └────┬───┘  └────┬─────┘  └────┬─────┘  │
│  钉钉机器人   │───▶│       │           │             │        │
└──────────────┘    │  ┌────▼───┐  ┌────▼─────┐  ┌────▼─────┐  │
                    │  │ LLM 抽象│  │ Mock API │  │ ChromaDB │  │
                    │  │Claude/  │  │ (HTTP)   │  │ (内嵌)   │  │
                    │  │ OpenAI  │  └──────────┘  └──────────┘  │
                    │  └────────┘   Redis(会话) │ SQLite(日志) │
                    └─────────────────────────────────────────┘
```

**技术栈**
- 后端：Python 3.12 · FastAPI · `uv` · SQLModel(SQLite) · ChromaDB(内嵌) · Redis · tiktoken
- LLM：Claude / OpenAI 双适配（`LLMClient` 抽象），tenacity 重试
- Embedding：OpenAI / Voyage AI / 本地 sentence-transformers 三选一（`EmbeddingClient` 抽象）
- 前端：Next.js 15 (App Router) · React 19 · Tailwind v4 (CSS-first) · pnpm
- 工程：Docker Compose · pytest · loguru · Langfuse · MCP

> 设计说明详见 [规划.md](规划.md)。

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填入 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL

# 2. 一键启动（backend + frontend + mock-api + redis）
./scripts/start.sh        # 或 docker compose up -d --build

# 3. 灌入知识库种子文档（docs/ 下的手册、FAQ 等）
./scripts/seed.sh
```

启动后：
- 管理后台 👉 http://localhost:3000/admin
- 对话页面 👉 http://localhost:3000/chat
- 后端 API 文档 👉 http://localhost:8000/docs

### 方式二：本地开发

```bash
# 后端
cd backend
uv sync                                   # 安装依赖
uv run uvicorn app.main:app --reload      # :8000

# Mock 内部 API（另开终端）
cd mock-api && uv run uvicorn main:app --port 8001

# 前端（另开终端）
cd frontend
pnpm install
pnpm dev                                  # :3000

# Redis（可选，未启动时自动降级为无记忆）
docker run -d -p 6379:6379 redis:7-alpine
```

## 🔑 关键配置（.env）

| 变量 | 说明 |
| --- | --- |
| `LLM_PROVIDER` | `openai` 或 `claude` |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | OpenAI 兼容代理配置 |
| `EMBEDDING_PROVIDER` | `openai` / `voyage` / `local` |
| `INPUT_PRICE_PER_M` / `OUTPUT_PRICE_PER_M` | Token 单价（美元/百万），用于成本核算 |
| `REDIS_URL` | 会话上下文存储 |
| `DINGTALK_APP_SECRET` 等 | 钉钉机器人验签 |
| `LANGFUSE_ENABLED` + keys | 可观测性（可选） |

> 完整变量见 [.env.example](.env.example)。**`.env` 已被 `.gitignore` 忽略，切勿提交密钥。**

## 🧪 测试与评测

```bash
# 单元/集成测试
./scripts/test.sh                       # 或 cd backend && uv run pytest

# 离线评测（需可用 API Key + 已索引知识库）
cd backend && uv run python -m evals.run_evals
cd backend && uv run python -m evals.run_evals --json report.json
```

测试覆盖：RAG 切片/检索、文档 API、Agent 工具选择与多轮上下文、内部 API 工具、钉钉验签与解析、设置接口、MCP 工具暴露。

## 🔌 MCP Server

```bash
cd backend && uv run python -m mcp_server   # stdio 传输
```

在 Claude Desktop / Cursor 中配置后，即可直接调用小苏的知识库检索与内部数据查询工具。

## 📁 目录结构

```
.
├── backend/            # FastAPI 后端
│   ├── app/
│   │   ├── api/        # 路由：documents / chat / logs / webhooks / settings
│   │   ├── services/   # agent / rag / session / llm / im
│   │   ├── tools/      # 工具注册表与实现
│   │   ├── models/     # SQLModel / Pydantic 模型
│   │   └── core/       # config / logging / observability
│   ├── evals/          # 离线评测
│   ├── tests/          # pytest
│   └── mcp_server.py   # MCP Server
├── frontend/           # Next.js 管理后台 + 聊天页
├── mock-api/           # 模拟内部 HR/订单 API
├── docs/               # 知识库种子文档 + 提交材料
├── scripts/            # start / test / seed / deploy
└── docker-compose.yml
```

## 📄 提交材料

- [AI 使用情况说明](docs/submission/AI_USAGE.md)
- [项目自评](docs/submission/自评.md)
