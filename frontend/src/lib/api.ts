import type {
  DocumentItem,
  DocumentChunks,
  ConversationLogItem,
  LogStats,
  SettingsInfo,
  StreamEvent,
} from "./types";

// 前端通过 Next.js rewrites 透传到后端，统一走相对路径 /api
const BASE = "/api";

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`;
    try {
      const data = await resp.json();
      detail = data.detail ?? detail;
    } catch {
      /* 非 JSON 错误体，忽略 */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

// ── 文档 ──────────────────────────────────────────────
export async function listDocuments(): Promise<DocumentItem[]> {
  return handle(await fetch(`${BASE}/documents`, { cache: "no-store" }));
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const form = new FormData();
  form.append("file", file);
  return handle(await fetch(`${BASE}/documents`, { method: "POST", body: form }));
}

export async function deleteDocument(id: string): Promise<void> {
  const resp = await fetch(`${BASE}/documents/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`删除失败 (${resp.status})`);
}

export async function getDocumentChunks(id: string): Promise<DocumentChunks> {
  return handle(await fetch(`${BASE}/documents/${id}/chunks`, { cache: "no-store" }));
}

// ── 日志 ──────────────────────────────────────────────
export async function listLogs(params: {
  platform?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<ConversationLogItem[]> {
  const q = new URLSearchParams();
  if (params.platform) q.set("platform", params.platform);
  q.set("limit", String(params.limit ?? 50));
  q.set("offset", String(params.offset ?? 0));
  return handle(await fetch(`${BASE}/logs?${q}`, { cache: "no-store" }));
}

export async function getLogStats(): Promise<LogStats> {
  return handle(await fetch(`${BASE}/logs/stats`, { cache: "no-store" }));
}

// ── 设置 ──────────────────────────────────────────────
export async function getSettings(): Promise<SettingsInfo> {
  return handle(await fetch(`${BASE}/settings`, { cache: "no-store" }));
}

// ── 聊天（非流式，留作兜底）────────────────────────────
export async function chat(message: string, sessionId: string) {
  return handle(
    await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    })
  );
}

// ── 聊天（SSE 流式）────────────────────────────────────
// 使用原生 EventSource 不便携带自定义逻辑，这里用 fetch + ReadableStream 解析 SSE。
export async function* chatStream(
  message: string,
  sessionId: string,
  signal?: AbortSignal
): AsyncGenerator<StreamEvent> {
  const q = new URLSearchParams({ message, session_id: sessionId });
  const resp = await fetch(`${BASE}/chat/stream?${q}`, {
    headers: { Accept: "text/event-stream" },
    signal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`流式请求失败 (${resp.status})`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE 以空行分隔事件
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part
        .split("\n")
        .find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload || payload === "[DONE]") continue;
      try {
        yield JSON.parse(payload) as StreamEvent;
      } catch {
        /* 跳过无法解析的片段 */
      }
    }
  }
}
