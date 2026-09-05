"use client";

import { useState, useEffect } from "react";
import { sessionApi, Session } from "@/lib/api";
import { Plus, MessageSquare, Trash2 } from "lucide-react";

interface Props {
  libraryId: string;
  activeSessionId: string | null;
  onSelectSession: (id: string | null) => void;
  refreshKey?: number;
}

export function SessionList({ libraryId, activeSessionId, onSelectSession, refreshKey }: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    sessionApi.list(libraryId).then(setSessions).catch(console.error);
  }, [libraryId, refreshKey]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const session = await sessionApi.create(libraryId, "Đoạn chat mới");
      setSessions((prev) => [session, ...prev]);
      onSelectSession(session.id);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (sessionId: string) => {
    if (!confirm("Xóa đoạn chat này?")) return;
    try {
      await sessionApi.delete(libraryId, sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) onSelectSession(null);
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <>
      {/* Header */}
      <div className="p-4 border-b border-[var(--border-color)]">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Đoạn chat</h2>
          <span className="text-xs text-[var(--text-muted)]">{sessions.length}</span>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="btn-secondary w-full justify-center text-xs py-2"
        >
          <Plus size={14} /> Chat mới
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-6 text-center">
            <MessageSquare size={28} className="mx-auto mb-2 text-[var(--text-muted)]" />
            <p className="text-sm text-[var(--text-muted)]">Chưa có đoạn chat</p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={`group flex items-center gap-3 px-4 py-3 cursor-pointer border-b border-[var(--border-color)] transition-all ${
                activeSessionId === session.id
                  ? "bg-[var(--accent-glow)] border-l-2 border-l-[var(--accent)]"
                  : "hover:bg-[var(--bg-hover)]"
              }`}
            >
              <MessageSquare
                size={16}
                className={
                  activeSessionId === session.id
                    ? "text-[var(--accent)] shrink-0"
                    : "text-[var(--text-muted)] shrink-0"
                }
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate text-[var(--text-primary)]">
                  {session.title || "Đoạn chat"}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  {new Date(session.updated_at).toLocaleDateString("vi-VN")}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(session.id);
                }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-[var(--bg-tertiary)] rounded shrink-0"
              >
                <Trash2 size={13} className="text-[var(--text-muted)]" />
              </button>
            </div>
          ))
        )}
      </div>
    </>
  );
}
