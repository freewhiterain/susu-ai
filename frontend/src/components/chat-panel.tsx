"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatStream, listDocuments, getDocumentChunks } from "@/lib/api";
import type { ChatMessage, Reference, DocumentChunk } from "@/lib/types";

// 来源跳转目标：定位到某文件的某一段
type RefTarget = { filename: string; chunkIndex: number };

const TOOL_LABELS: Record<string, string> = {
  search_docs: "📚 检索知识库",
  get_current_time: "🕐 查询当前时间",
  get_employee: "👤 查询员工信息",
  get_attendance: "📅 查询考勤记录",
  get_orders: "🧾 查询订单数据",
};

function genSessionId(): string {
  return "web-" + Math.random().toString(36).slice(2, 10);
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [refTarget, setRefTarget] = useState<RefTarget | null>(null);
  const sessionId = useRef<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    sessionId.current = genSessionId();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);

    const userMsg: ChatMessage = { role: "user", content: text };
    const assistantMsg: ChatMessage = { role: "assistant", content: "", pending: true, tools: [] };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const ac = new AbortController();
    abortRef.current = ac;

    // 局部累积，避免频繁 setState 闭包问题
    let content = "";
    let refs: Reference[] = [];
    const tools: ChatMessage["tools"] = [];
    let usage: ChatMessage["usage"];

    const flush = () => {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content,
          references: refs,
          tools: [...(tools ?? [])],
          usage,
          pending: true,
        };
        return next;
      });
    };

    try {
      for await (const ev of chatStream(text, sessionId.current, ac.signal)) {
        switch (ev.type) {
          case "tool_start":
            tools?.push({ name: ev.name, input: ev.input });
            flush();
            break;
          case "tool_result":
            // 标记对应工具已完成
            if (tools) {
              const t = [...tools].reverse().find((x) => x.name === ev.name && !x.result);
              if (t) t.result = ev.result;
            }
            flush();
            break;
          case "text":
            content += ev.delta;
            flush();
            break;
          case "references":
            refs = ev.data ?? [];
            flush();
            break;
          case "done":
            usage = {
              input_tokens: ev.input_tokens,
              output_tokens: ev.output_tokens,
              cost_usd: ev.cost_usd,
              latency_ms: ev.latency_ms,
            };
            break;
          case "error":
            content = content || ev.message;
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { role: "assistant", content, error: true };
              return next;
            });
            break;
        }
      }
    } catch (e) {
      if (!ac.signal.aborted) {
        content = content || "请求失败：" + (e instanceof Error ? e.message : String(e));
      }
    } finally {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: content || "（无回复）",
          references: refs,
          tools: [...(tools ?? [])],
          usage,
          pending: false,
        };
        return next;
      });
      setBusy(false);
      abortRef.current = null;
    }
  }, [input, busy]);

  const stop = () => {
    abortRef.current?.abort();
    setBusy(false);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 消息区 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center text-[var(--text-muted)]">
            <div className="w-14 h-14 rounded-2xl bg-brand text-white text-2xl font-bold flex items-center justify-center mb-4">
              苏
            </div>
            <p className="text-lg font-medium text-[var(--text)]">你好，我是小苏</p>
            <p className="mt-1 text-sm">可以问我公司制度、考勤、报销、员工信息等问题</p>
            <div className="mt-5 flex flex-wrap gap-2 justify-center max-w-md">
              {["年假有多少天？", "报销流程是怎样的？", "查一下张三的考勤", "现在几点了"].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="px-3 py-1.5 text-sm rounded-full border border-[var(--border)] bg-white hover:bg-slate-50 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} onOpenRef={setRefTarget} />
        ))}
      </div>

      {refTarget && (
        <DocViewerModal target={refTarget} onClose={() => setRefTarget(null)} />
      )}

      {/* 输入区 */}
      <div className="border-t border-[var(--border)] bg-white px-4 py-3">
        <div className="flex items-end gap-2 max-w-3xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            rows={1}
            placeholder="输入问题，Enter 发送，Shift+Enter 换行"
            className="flex-1 resize-none rounded-xl border border-[var(--border)] px-4 py-3 focus:outline-none focus:ring-2 focus:ring-brand/40 max-h-40"
          />
          {busy ? (
            <button
              onClick={stop}
              className="px-5 py-3 rounded-xl bg-slate-200 text-slate-700 font-medium hover:bg-slate-300 transition"
            >
              停止
            </button>
          ) : (
            <button
              onClick={send}
              disabled={!input.trim()}
              className="px-5 py-3 rounded-xl bg-brand text-white font-medium hover:bg-brand-dark transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  msg,
  onOpenRef,
}: {
  msg: ChatMessage;
  onOpenRef: (t: RefTarget) => void;
}) {
  const isUser = msg.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-brand text-white px-4 py-2.5 whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="shrink-0 w-8 h-8 rounded-lg bg-brand text-white text-sm font-bold flex items-center justify-center">
        苏
      </div>
      <div className="flex-1 max-w-[85%] space-y-2">
        {/* 工具调用指示 */}
        {msg.tools && msg.tools.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {msg.tools.map((t, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-brand-light text-brand-dark"
              >
                {TOOL_LABELS[t.name] ?? t.name}
                {t.result ? " ✓" : " …"}
              </span>
            ))}
          </div>
        )}

        {/* 正文 */}
        <div
          className={`markdown-body rounded-2xl rounded-tl-sm px-4 py-2.5 ${
            msg.error ? "bg-red-50 text-red-700" : "bg-white border border-[var(--border)]"
          }`}
        >
          {msg.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          ) : msg.pending ? (
            <span className="inline-flex gap-1 text-[var(--text-muted)]">
              <Dot /> <Dot /> <Dot />
            </span>
          ) : null}
        </div>

        {/* 引用来源：可点击跳转到原文并高亮 */}
        {msg.references && msg.references.length > 0 && (
          <details className="text-sm bg-slate-50 border border-[var(--border)] rounded-xl px-3 py-2">
            <summary className="cursor-pointer text-[var(--text-muted)] font-medium">
              📎 参考来源 ({msg.references.length})
            </summary>
            <div className="mt-2 space-y-2">
              {msg.references.map((r, i) => (
                <button
                  key={i}
                  onClick={() =>
                    onOpenRef({ filename: r.filename, chunkIndex: r.chunk_index })
                  }
                  title="点击查看原文位置"
                  className="block w-full text-left border-l-2 border-brand pl-2 py-1 rounded-r hover:bg-brand-light/60 transition group"
                >
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-medium text-brand-dark group-hover:underline">
                      📄 {r.filename}
                    </span>
                    <span className="text-[var(--text-muted)]">
                      第 {r.chunk_index + 1} 段 · 相关度 {(r.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 mt-0.5 line-clamp-2 whitespace-pre-wrap">
                    {r.snippet.replace(/^【来源：.+?】\s*/, "")}
                  </div>
                </button>
              ))}
            </div>
          </details>
        )}

        {/* Token / 成本 */}
        {msg.usage && (
          <div className="text-xs text-[var(--text-muted)]">
            输入 {msg.usage.input_tokens} · 输出 {msg.usage.output_tokens} tokens · 成本 $
            {msg.usage.cost_usd.toFixed(6)} · 耗时 {msg.usage.latency_ms}ms
          </div>
        )}
      </div>
    </div>
  );
}

function Dot() {
  return <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse inline-block" />;
}

// 原文查看器：根据来源 filename 解析 doc_id → 拉取全部分块 → 高亮并滚动到引用段落
function DocViewerModal({
  target,
  onClose,
}: {
  target: RefTarget;
  onClose: () => void;
}) {
  const [chunks, setChunks] = useState<DocumentChunk[] | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const docs = await listDocuments();
        const doc = docs.find((d) => d.filename === target.filename);
        if (!doc) throw new Error("未找到对应文档（可能已删除）");
        const data = await getDocumentChunks(doc.id);
        if (!cancelled) setChunks(data.chunks);
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [target.filename]);

  // 加载完成后滚动到高亮段落
  useEffect(() => {
    if (chunks && activeRef.current) {
      activeRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [chunks]);

  // ESC 关闭
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)]">
          <div className="font-semibold flex items-center gap-2">
            📄 {target.filename}
            <span className="text-xs font-normal text-[var(--text-muted)]">
              已定位到第 {target.chunkIndex + 1} 段
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-2xl leading-none"
            aria-label="关闭"
          >
            ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {loading && <div className="text-[var(--text-muted)] text-sm">加载原文中…</div>}
          {err && <div className="text-red-600 text-sm">加载失败：{err}</div>}
          {chunks?.map((c) => {
            const active = c.chunk_index === target.chunkIndex;
            return (
              <div
                key={c.chunk_index}
                ref={active ? activeRef : undefined}
                className={`text-sm whitespace-pre-wrap rounded-lg px-3 py-2 border ${
                  active
                    ? "bg-yellow-50 border-yellow-300 ring-2 ring-yellow-200"
                    : "bg-slate-50 border-transparent text-slate-600"
                }`}
              >
                <div className="text-xs text-[var(--text-muted)] mb-1">
                  第 {c.chunk_index + 1} 段{active ? " · 引用位置" : ""}
                </div>
                {c.text}
              </div>
            );
          })}
          {chunks && chunks.length === 0 && (
            <div className="text-[var(--text-muted)] text-sm">该文档暂无可显示的分块。</div>
          )}
        </div>
      </div>
    </div>
  );
}
