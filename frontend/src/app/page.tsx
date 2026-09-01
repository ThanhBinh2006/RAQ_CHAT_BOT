"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { libraryApi, Library } from "@/lib/api";
import { Plus, BookOpen, LogOut, Settings, Trash2 } from "lucide-react";
import { ApiKeySettingsModal } from "@/components/settings/ApiKeySettingsModal";

export default function HomePage() {
  const { user, token, logout } = useAuth();
  const router = useRouter();
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!token) {
      router.push("/auth");
    }
  }, [token, router]);

  // Fetch libraries
  useEffect(() => {
    if (token) {
      libraryApi.list().then(setLibraries).catch(console.error);
    }
  }, [token]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setLoading(true);
    try {
      const lib = await libraryApi.create({ name: newName, description: newDesc });
      setLibraries((prev) => [lib, ...prev]);
      setNewName("");
      setNewDesc("");
      setShowCreate(false);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Xóa thư viện này và toàn bộ dữ liệu?")) return;
    try {
      await libraryApi.delete(id);
      setLibraries((prev) => prev.filter((l) => l.id !== id));
    } catch (e: any) {
      alert(e.message);
    }
  };

  if (!token) return null;

  const COLORS = [
    "from-indigo-500 to-purple-600",
    "from-cyan-500 to-blue-600",
    "from-emerald-500 to-teal-600",
    "from-orange-500 to-red-600",
    "from-pink-500 to-rose-600",
    "from-violet-500 to-fuchsia-600",
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <BookOpen size={18} className="text-white" />
          </div>
          <h1 className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            RAQ Chatbot
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-[var(--text-secondary)]">{user?.email}</span>
          <button onClick={() => setShowSettings(true)} className="btn-secondary" title="Cài đặt API Key">
            <Settings size={16} />
          </button>
          <button onClick={logout} className="btn-secondary" title="Đăng xuất">
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">Thư viện của tôi</h2>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              Quản lý kho tri thức và tạo đề trắc nghiệm
            </p>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            <Plus size={16} /> Tạo Thư viện
          </button>
        </div>

        {/* Create Modal */}
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="glass-card p-6 w-full max-w-md animate-fade-in">
              <h3 className="text-lg font-semibold mb-4">Tạo Thư viện mới</h3>
              <input
                className="input-field mb-3"
                placeholder="Tên thư viện..."
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                autoFocus
              />
              <input
                className="input-field mb-4"
                placeholder="Mô tả (tùy chọn)..."
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
              />
              <div className="flex gap-3 justify-end">
                <button className="btn-secondary" onClick={() => setShowCreate(false)}>
                  Hủy
                </button>
                <button className="btn-primary" onClick={handleCreate} disabled={loading || !newName.trim()}>
                  {loading ? "Đang tạo..." : "Tạo"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Library Grid */}
        {libraries.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-[var(--bg-tertiary)] flex items-center justify-center">
              <BookOpen size={32} className="text-[var(--text-muted)]" />
            </div>
            <p className="text-[var(--text-muted)] text-lg">Chưa có thư viện nào</p>
            <p className="text-[var(--text-muted)] text-sm mt-1">Tạo thư viện đầu tiên để bắt đầu</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {libraries.map((lib, i) => (
              <div
                key={lib.id}
                className="glass-card group cursor-pointer hover:border-[var(--border-hover)] transition-all duration-200 animate-fade-in"
                style={{ animationDelay: `${i * 50}ms` }}
                onClick={() => router.push(`/libraries/${lib.id}`)}
              >
                <div className={`h-2 rounded-t-[var(--radius-lg)] bg-gradient-to-r ${COLORS[i % COLORS.length]}`} />
                <div className="p-5">
                  <div className="flex items-start justify-between">
                    <h3 className="font-semibold text-[var(--text-primary)] line-clamp-1">{lib.name}</h3>
                    <button
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-[var(--bg-hover)] rounded"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(lib.id);
                      }}
                    >
                      <Trash2 size={14} className="text-[var(--text-muted)]" />
                    </button>
                  </div>
                  {lib.description && (
                    <p className="text-sm text-[var(--text-muted)] mt-1 line-clamp-2">{lib.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-3 text-xs text-[var(--text-secondary)]">
                    <span>{lib.total_documents} tài liệu</span>
                    <span>•</span>
                    <span>{new Date(lib.created_at).toLocaleDateString("vi-VN")}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Settings Modal */}
      {showSettings && <ApiKeySettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}
