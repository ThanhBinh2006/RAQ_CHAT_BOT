"use client";

import { useState, useEffect, useRef } from "react";
import { documentApi, Document, IngestionProgress } from "@/lib/api";
import { Upload, FileText, Trash2, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

interface Props {
  libraryId: string;
}

export function LibrarySidebar({ libraryId }: Props) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progressMap, setProgressMap] = useState<Record<string, IngestionProgress>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch documents
  useEffect(() => {
    documentApi.list(libraryId).then(setDocuments).catch(console.error);
  }, [libraryId]);

  // Poll progress for processing documents
  useEffect(() => {
    const processingDocs = documents.filter((d) => d.status === "processing");
    if (processingDocs.length === 0) return;

    const interval = setInterval(async () => {
      for (const doc of processingDocs) {
        try {
          const progress = await documentApi.progress(doc.id);
          setProgressMap((prev) => ({ ...prev, [doc.id]: progress }));
          if (progress.status === "ready" || progress.status === "failed") {
            setDocuments((prev) =>
              prev.map((d) => (d.id === doc.id ? { ...d, status: progress.status } : d))
            );
          }
        } catch {}
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [documents]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const doc = await documentApi.upload(libraryId, file);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("Xóa tài liệu này?")) return;
    try {
      await documentApi.delete(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: any) {
      alert(err.message);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "ready":
        return <CheckCircle size={14} className="text-[var(--success)]" />;
      case "processing":
        return <Loader2 size={14} className="text-[var(--accent)] animate-spin" />;
      case "failed":
        return <AlertCircle size={14} className="text-[var(--danger)]" />;
      default:
        return <Loader2 size={14} className="text-[var(--text-muted)]" />;
    }
  };

  return (
    <>
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Tài liệu</h2>
          <span className="text-xs text-[var(--text-muted)]">{documents.length} file</span>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleUpload}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="btn-primary w-full justify-center text-xs py-2"
        >
          {uploading ? (
            <><Loader2 size={14} className="animate-spin" /> Đang tải lên...</>
          ) : (
            <><Upload size={14} /> Upload PDF</>
          )}
        </button>
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto">
        {documents.length === 0 ? (
          <div className="p-6 text-center">
            <FileText size={28} className="mx-auto mb-2 text-[var(--text-muted)]" />
            <p className="text-sm text-[var(--text-muted)]">Chưa có tài liệu</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">Upload file PDF để bắt đầu</p>
          </div>
        ) : (
          documents.map((doc) => {
            const progress = progressMap[doc.id];
            return (
              <div
                key={doc.id}
                className="group flex items-start gap-3 px-4 py-3 border-b border-[var(--border-color)] hover:bg-[var(--bg-hover)] transition-colors animate-slide-in"
              >
                <div className="shrink-0 mt-0.5">{getStatusIcon(doc.status)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--text-primary)] truncate font-medium">
                    {doc.file_name}
                  </p>
                  {doc.total_pages && (
                    <p className="text-xs text-[var(--text-muted)]">{doc.total_pages} trang</p>
                  )}
                  {doc.status === "processing" && progress && (
                    <div className="mt-2">
                      <div className="progress-bar-container">
                        <div
                          className="progress-bar-fill"
                          style={{ width: `${progress.progress_percent}%` }}
                        />
                      </div>
                      <p className="text-xs text-[var(--text-muted)] mt-1">
                        {progress.processed_chunks}/{progress.total_chunks} chunks (
                        {Math.round(progress.progress_percent)}%)
                      </p>
                    </div>
                  )}
                  {doc.status === "failed" && progress?.error_message && (
                    <p className="text-xs text-[var(--danger)] mt-1">{progress.error_message}</p>
                  )}
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-[var(--bg-tertiary)] rounded shrink-0"
                >
                  <Trash2 size={13} className="text-[var(--text-muted)]" />
                </button>
              </div>
            );
          })
        )}
      </div>
    </>
  );
}
