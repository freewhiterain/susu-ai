"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { listDocuments, uploadDocument, deleteDocument } from "@/lib/api";
import type { DocumentItem, IndexStatus } from "@/lib/types";

const STATUS_BADGE: Record<IndexStatus, { label: string; cls: string }> = {
  pending: { label: "索引中", cls: "bg-amber-100 text-amber-700" },
  indexed: { label: "已索引", cls: "bg-green-100 text-green-700" },
  failed: { label: "失败", cls: "bg-red-100 text-red-700" },
};

const ACCEPT = ".md,.txt,.pdf,.docx";

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const d = await listDocuments();
      setDocs(d);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // 有 pending 文档时轮询刷新索引状态
  useEffect(() => {
    const hasPending = docs.some((d) => d.status === "pending");
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(load, 2000);
    } else if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [docs, load]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      setUploading(true);
      setError("");
      try {
        for (const file of Array.from(files)) {
          await uploadDocument(file);
        }
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setUploading(false);
        if (fileInput.current) fileInput.current.value = "";
      }
    },
    [load]
  );

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除文档「${name}」？此操作会同时移除其向量索引。`)) return;
    try {
      await deleteDocument(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">知识库</h1>
      <p className="text-[var(--text-muted)] mb-6">
        上传公司文档，自动切片、向量化并加入检索库。支持 Markdown / TXT / PDF / Word。
      </p>

      {/* 上传区 */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInput.current?.click()}
        className={`mb-6 cursor-pointer border-2 border-dashed rounded-xl px-6 py-10 text-center transition ${
          dragOver ? "border-brand bg-brand-light" : "border-[var(--border)] bg-white"
        }`}
      >
        <input
          ref={fileInput}
          type="file"
          accept={ACCEPT}
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {uploading ? (
          <p className="text-brand font-medium">上传并索引中…</p>
        ) : (
          <>
            <p className="font-medium">点击或拖拽文件到此处上传</p>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              支持 {ACCEPT}，同名文件将增量更新
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>
      )}

      {/* 文档列表 */}
      <div className="bg-white border border-[var(--border)] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-[var(--text-muted)]">
            <tr>
              <th className="text-left font-medium px-4 py-3">文件名</th>
              <th className="text-left font-medium px-4 py-3">类型</th>
              <th className="text-left font-medium px-4 py-3">大小</th>
              <th className="text-left font-medium px-4 py-3">片段</th>
              <th className="text-left font-medium px-4 py-3">状态</th>
              <th className="text-left font-medium px-4 py-3">更新时间</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-[var(--text-muted)]">
                  加载中…
                </td>
              </tr>
            ) : docs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-[var(--text-muted)]">
                  暂无文档，上传第一个吧
                </td>
              </tr>
            ) : (
              docs.map((d) => {
                const badge = STATUS_BADGE[d.status];
                return (
                  <tr key={d.id} className="border-t border-[var(--border)]">
                    <td className="px-4 py-3 font-medium">{d.filename}</td>
                    <td className="px-4 py-3 uppercase text-[var(--text-muted)]">{d.file_type}</td>
                    <td className="px-4 py-3">{fmtSize(d.file_size)}</td>
                    <td className="px-4 py-3">{d.chunk_count}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${badge.cls}`}>
                        {badge.label}
                      </span>
                      {d.status === "failed" && d.error_msg && (
                        <span className="block text-xs text-red-500 mt-1" title={d.error_msg}>
                          {d.error_msg.slice(0, 40)}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-[var(--text-muted)]">
                      {new Date(d.updated_at).toLocaleString("zh-CN")}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDelete(d.id, d.filename)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
