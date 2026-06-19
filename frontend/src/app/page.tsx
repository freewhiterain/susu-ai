import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="max-w-2xl text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand text-white text-3xl font-bold mb-6">
          苏
        </div>
        <h1 className="text-4xl font-bold mb-3">小苏 · 企业 AI 助手</h1>
        <p className="text-[var(--text-muted)] text-lg mb-10">
          基于公司知识库的智能问答，支持文档检索、工具调用与多渠道接入。
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/chat"
            className="px-6 py-3 rounded-xl bg-brand text-white font-medium hover:bg-brand-dark transition"
          >
            开始对话
          </Link>
          <Link
            href="/admin"
            className="px-6 py-3 rounded-xl border border-[var(--border)] bg-white font-medium hover:bg-slate-50 transition"
          >
            管理后台
          </Link>
        </div>
      </div>
    </main>
  );
}
