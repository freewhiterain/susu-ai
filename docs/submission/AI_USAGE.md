# AI 使用情况说明

> 本项目在开发全程深度使用 AI 编码助手（Claude Code）。本文如实记录 AI 的参与方式、产出边界与人工把控点，供评审参考。

## 一、使用的 AI 工具

| 工具 | 用途 |
| --- | --- |
| Claude Code（claude-sonnet / opus） | 需求拆解、技术方案、代码生成、测试编写、文档撰写、问题排查 |

## 二、AI 在各阶段的参与

### 1. 需求分析与方案设计
- 通读笔试题，提炼必做项与加分项，输出 [规划.md](../../规划.md)。
- AI 给出初版架构后，**人工复核发现并纠正多处问题**（见下「人工纠偏」），AI 据此重构方案。

### 2. 后端实现
- LLM 抽象层（Claude/OpenAI 双适配）、RAG Pipeline（解析/切片/向量化/检索）、Agent 主循环、工具层、钉钉适配器、各 API 路由，均由 AI 生成主体代码。
- 人工逐文件审阅接口契约、错误处理、降级逻辑，并指定关键设计（如 `EmbeddingClient` 与 `LLMClient` 分离、ChromaDB 内嵌、Token 单价走环境变量）。

### 3. 前端实现
- Next.js 15 管理后台与聊天页（含 SSE 流式解析、工具调用指示、引用展示、成本显示）由 AI 生成。
- 人工确认前后端数据结构严格对齐（AI 主动回读后端模型后修正了 `types.ts`）。

### 4. 测试与评测
- pytest 用例（RAG / API / Agent / 工具 / IM / 设置 / MCP）与 20 条离线评测用例由 AI 编写。
- 人工指定测试维度（工具选择正确率、引用合规率、拒答边界）。

### 5. 工程化与文档
- Dockerfile、docker-compose、运维脚本、README、本说明由 AI 生成，人工审阅可执行性。

## 三、人工纠偏（AI 出错并被修正的关键点）

| 问题 | AI 初稿 | 纠正后 |
| --- | --- | --- |
| Embedding 抽象 | 把 `embed()` 放进 `LLMClient` | Claude 无 embedding API，拆出独立 `EmbeddingClient` |
| 向量库部署 | ChromaDB 单独起容器 | 改为 `PersistentClient` 内嵌进后端进程 |
| Tailwind 配置 | 生成 `tailwind.config.ts` | Tailwind v4 用 CSS-first，改 `globals.css` |
| Embedding 选型 | 仅列 OpenAI / 本地 | 补充 Anthropic 官方推荐的 Voyage AI |
| Langfuse 版本 | `langfuse>=2.0.0` | pin `<3.0.0`，避免 v3 重构导致 `trace()` API 失效 |

> 这些纠偏体现了「AI 提速、人工把关」的协作方式：AI 负责广度与速度，工程决策与正确性由人确认。

## 四、AI 未参与/人工主导的部分
- API Key、`.env` 实际密钥由人工填写，**从未写入代码或提交版本库**（`.gitignore` 已排除）。
- 架构关键取舍、第三方服务选型、安全边界由人工决策。

## 五、自查：密钥安全
- 源码中无任何硬编码密钥；配置一律经 `pydantic-settings` 从 `.env` 读取。
- `.gitignore` 排除 `.env` 及 `*.key/*.pem`；提交前可执行 `git log -p | grep -i api_key` 自查应为空。
