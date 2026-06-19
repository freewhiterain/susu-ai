import Link from "next/link";
import ChatPanel from "@/components/chat-panel";

export default function ChatPage() {
  return (
    <div className="h-screen flex flex-col">
      <header className="shrink-0 border-b border-[var(--border)] bg-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand text-white text-sm font-bold flex items-center justify-center">
            苏
          </div>
          <span className="font-semibold">小苏 · 智能问答</span>
        </div>
        <Link
          href="/admin"
          className="text-sm text-[var(--text-muted)] hover:text-brand transition"
        >
          管理后台 →
        </Link>
      </header>
      <div className="flex-1 min-h-0">
        <div className="h-full max-w-3xl mx-auto">
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
