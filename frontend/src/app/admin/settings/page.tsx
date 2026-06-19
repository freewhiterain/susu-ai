"use client";

import { useEffect, useState } from "react";
import { getSettings } from "@/lib/api";
import type { SettingsInfo } from "@/lib/types";

export default function SettingsPage() {
  const [info, setInfo] = useState<SettingsInfo | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getSettings()
      .then(setInfo)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">系统设置</h1>
      <p className="text-[var(--text-muted)] mb-6">
        当前运行配置（只读）。修改请编辑后端 <code>.env</code> 后重启服务。
      </p>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm">
          加载失败：{error}
        </div>
      )}

      {!info ? (
        <div className="text-[var(--text-muted)]">加载中…</div>
      ) : (
        <div className="space-y-6">
          <Section title="模型配置">
            <Row label="对话模型提供方" value={info.llm_provider} />
            <Row label="对话模型" value={info.llm_model} mono />
            <Row label="向量模型提供方" value={info.embedding_provider} />
            <Row label="向量模型" value={info.embedding_model} mono />
            <Row label="工具调用最大轮次" value={String(info.max_tool_rounds)} />
          </Section>

          <Section title="计费（按百万 token）">
            <Row label="输入单价" value={`$${info.input_price_per_m} / 1M tokens`} />
            <Row label="输出单价" value={`$${info.output_price_per_m} / 1M tokens`} />
          </Section>

          <Section title="基础设施">
            <Row
              label="Redis 会话存储"
              value={info.redis_connected ? "已连接" : "未连接（降级为无记忆）"}
              status={info.redis_connected}
            />
            <Row
              label="Langfuse 可观测性"
              value={info.langfuse_enabled ? "已启用" : "未启用"}
              status={info.langfuse_enabled}
            />
          </Section>

          <Section title="IM 接入状态">
            {info.im_integrations.map((im) => (
              <Row
                key={im.platform}
                label={im.platform}
                value={
                  im.configured
                    ? `已接入 · ${im.webhook_path}${im.verify_enabled ? " · 已开启验签" : " · 未开启验签"}`
                    : "未接入（未配置密钥）"
                }
                status={im.configured}
              />
            ))}
          </Section>

          <Section title="知识库统计">
            <Row label="文档数量" value={String(info.document_count)} />
            <Row label="向量片段数" value={String(info.vector_count)} />
          </Section>
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="px-5 py-3 bg-slate-50 font-semibold border-b border-[var(--border)]">
        {title}
      </div>
      <div className="divide-y divide-[var(--border)]">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
  status,
}: {
  label: string;
  value: string;
  mono?: boolean;
  status?: boolean;
}) {
  return (
    <div className="px-5 py-3 flex items-center justify-between">
      <span className="text-[var(--text-muted)] text-sm">{label}</span>
      <span className={`text-sm flex items-center gap-2 ${mono ? "font-mono" : ""}`}>
        {status !== undefined && (
          <span
            className={`w-2 h-2 rounded-full ${status ? "bg-green-500" : "bg-slate-300"}`}
          />
        )}
        {value}
      </span>
    </div>
  );
}
