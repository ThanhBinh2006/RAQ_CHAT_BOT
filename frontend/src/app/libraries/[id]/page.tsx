"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { libraryApi, Library } from "@/lib/api";
import { LibrarySidebar } from "@/components/library/LibrarySidebar";
import { SessionList } from "@/components/library/SessionList";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ArrowLeft, Settings } from "lucide-react";
import { ApiKeySettingsModal } from "@/components/settings/ApiKeySettingsModal";

export default function LibraryPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const libraryId = params.id as string;

  const [library, setLibrary] = useState<Library | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    if (!token) {
      router.push("/auth");
      return;
    }
    libraryApi.get(libraryId).then(setLibrary).catch(() => router.push("/"));
  }, [token, libraryId, router]);

  if (!library) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top Bar */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="p-2 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
          >
            <ArrowLeft size={18} className="text-[var(--text-secondary)]" />
          </button>
          <div>
            <h1 className="text-sm font-semibold text-[var(--text-primary)]">{library.name}</h1>
            {library.description && (
              <p className="text-xs text-[var(--text-muted)]">{library.description}</p>
            )}
          </div>
        </div>
        <button onClick={() => setShowSettings(true)} className="btn-secondary text-xs">
          <Settings size={14} /> Cài đặt
        </button>
      </header>

      {/* 3-Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Column 1: Documents Sidebar */}
        <div className="w-72 border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col shrink-0">
          <LibrarySidebar libraryId={libraryId} />
        </div>

        {/* Column 2: Chat Sessions */}
        <div className="w-64 border-r border-[var(--border-color)] bg-[var(--bg-secondary)] flex flex-col shrink-0">
          <SessionList
            libraryId={libraryId}
            activeSessionId={activeSessionId}
            onSelectSession={setActiveSessionId}
          />
        </div>

        {/* Column 3: Chat Window */}
        <div className="flex-1 flex flex-col bg-[var(--bg-primary)]">
          <ChatWindow libraryId={libraryId} sessionId={activeSessionId} />
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && <ApiKeySettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}
