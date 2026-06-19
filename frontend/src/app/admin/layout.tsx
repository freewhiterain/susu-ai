"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/admin", label: "概览", icon: "📊" },
  { href: "/admin/documents", label: "知识库", icon: "📚" },
  { href: "/admin/logs", label: "对话日志", icon: "💬" },
  { href: "/admin/settings", label: "系统设置", icon: "⚙️" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen">
      {/* 侧边栏 */}
      <aside className="w-56 shrink-0 border-r border-[var(--border)] bg-white flex flex-col">
        <div className="px-5 py-4 flex items-center gap-2 border-b border-[var(--border)]">
          <div className="w-8 h-8 rounded-lg bg-brand text-white text-sm font-bold flex items-center justify-center">
            苏
          </div>
          <span className="font-semibold">小苏管理后台</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map((item) => {
            const active =
              item.href === "/admin"
                ? pathname === "/admin"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                  active
                    ? "bg-brand-light text-brand-dark font-medium"
                    : "text-[var(--text-muted)] hover:bg-slate-50"
                }`}
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-[var(--border)]">
          <Link
            href="/chat"
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-brand hover:bg-brand-light transition"
          >
            💡 前往对话页
          </Link>
        </div>
      </aside>

      {/* 内容区 */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
