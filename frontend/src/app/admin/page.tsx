"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getLogStats, listDocuments } from "@/lib/api";
import type { LogStats, DocumentItem } from "@/lib/types";

export default function AdminOverview() {
  const [stats, setStats] = useState<LogStats | null>(null);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getLogStats(), listDocuments()])
      .then(([s, d]) => {
        setStats(s);
        setDocs(d);
      })
      .catch((e) => setError(e.message));
  }, []);

  const indexed = docs.filter((d) => d.status === "indexed").length;
  const chunks = docs.reduce((sum, d) => sum + d.chunk_count, 0);

  const cards = [
    { label: "今日对话数", value: stats?.today_conversations ?? "—", suffix: "次" },
    { label: "累计对话数", value: stats?.total_conversations ?? "—", suffix: "次" },
    {
      label: "今日 Token",
      value:
        stats != null
          ? (stats.today_input_tokens + stats.today_output_tokens).toLocaleString()
          : "—",
      suffix: "",
    },
    {
      label: "今日成本",
      value: stats != null ? `$${stats.today_cost_usd.toFixed(4)}` : "—",
      suffix: "",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">概览</h1>
      <p className="text-[var(--text-muted)] mb-6">系统运行状态与关键指标</p>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm">
          加载失败：{error}（请确认后端已启动）
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className="bg-white border border-[var(--border)] rounded-xl p-5">
            <div className="text-sm text-[var(--text-muted)]">{c.label}</div>
            <div className="mt-2 text-2xl font-bold">
              {c.value}
              {c.suffix && <span className="text-base font-normal ml-1">{c.suffix}</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">知识库</h2>
            <Link href="/admin/documents" className="text-sm text-brand hover:underline">
              管理 →
            </Link>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <Stat label="文档总数" value={docs.length} />
            <Stat label="已索引" value={indexed} />
            <Stat label="向量片段" value={chunks} />
          </div>
        </div>

        <div className="bg-white border border-[var(--border)] rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">快捷入口</h2>
          </div>
          <div className="space-y-2">
            <Link
              href="/admin/documents"
              className="block px-3 py-2 rounded-lg hover:bg-slate-50 text-sm"
            >
              📚 上传 / 管理文档
            </Link>
            <Link
              href="/admin/logs"
              className="block px-3 py-2 rounded-lg hover:bg-slate-50 text-sm"
            >
              💬 查看对话日志与成本
            </Link>
            <Link
              href="/chat"
              className="block px-3 py-2 rounded-lg hover:bg-slate-50 text-sm"
            >
              🤖 体验智能问答
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-[var(--text-muted)] mt-1">{label}</div>
    </div>
  );
}
