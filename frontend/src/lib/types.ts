// 与后端 Pydantic / SQLModel 模型严格对齐

// ── 文档 (DocumentRead) ───────────────────────────────
export type IndexStatus = "pending" | "indexed" | "failed";

export interface DocumentItem {
  id: string; // uuid
  filename: string;
  file_type: string; // md | pdf | docx | txt
  file_size: number;
  status: IndexStatus;
  chunk_count: number;
  error_msg: string;
  created_at: string;
  updated_at: string;
}

// ── 聊天 ──────────────────────────────────────────────
// 后端引用结构当前只含 snippet（内嵌【来源：xxx】）
export interface Reference {
  snippet: string;
}

export interface ToolCallInfo {
  name: string;
  input: Record<string, unknown>;
  result: string;
}

// 前端聊天气泡
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  references?: Reference[];
  tools?: { name: string; input?: Record<string, unknown>; result?: string }[];
  usage?: { input_tokens: number; output_tokens: number; cost_usd: number; latency_ms: number };
  pending?: boolean;
  error?: boolean;
}

// SSE 事件（与 agent.run_stream 输出严格对齐）
export type StreamEvent =
  | { type: "tool_start"; name: string; input: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: string }
  | { type: "text"; delta: string }
  | { type: "references"; data: Reference[] }
  | {
      type: "done";
      session_id: string;
      input_tokens: number;
      output_tokens: number;
      cost_usd: number;
      latency_ms: number;
    }
  | { type: "error"; message: string };

// ── 日志 (ConversationLogRead) ────────────────────────
export interface ConversationLogItem {
  id: number;
  session_id: string;
  platform: string;
  user_id: string;
  user_msg: string;
  assistant_msg: string;
  tools_called: string; // JSON 字符串
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  has_reference: boolean;
  created_at: string;
}

export interface LogStats {
  total_conversations: number;
  today_conversations: number;
  today_input_tokens: number;
  today_output_tokens: number;
  today_cost_usd: number;
}

// ── 设置 (Phase 6 /api/settings) ──────────────────────
export interface ImIntegration {
  platform: string;
  configured: boolean;
  webhook_path: string;
  verify_enabled: boolean;
}

export interface SettingsInfo {
  llm_provider: string;
  llm_model: string;
  embedding_provider: string;
  embedding_model: string;
  input_price_per_m: number;
  output_price_per_m: number;
  max_tool_rounds: number;
  langfuse_enabled: boolean;
  redis_connected: boolean;
  document_count: number;
  vector_count: number;
  im_integrations: ImIntegration[];
}
