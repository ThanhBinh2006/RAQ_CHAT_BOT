"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { BookOpen, Eye, EyeOff } from "lucide-react";

export default function AuthPage() {
  const { login, register } = useAuth();
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, firstName, lastName);
      }
      router.push("/");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      {/* Background glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-indigo-500/5 blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-purple-500/5 blur-3xl" />
      </div>

      <div className="glass-card w-full max-w-md p-8 animate-fade-in relative z-10">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
            <BookOpen size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              RAQ Chatbot
            </h1>
            <p className="text-xs text-[var(--text-muted)]">Trợ lý Thư viện Tri thức</p>
          </div>
        </div>

        {/* Tab Switch */}
        <div className="flex mb-6 bg-[var(--bg-primary)] rounded-lg p-1">
          <button
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
              isLogin ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)] shadow-sm" : "text-[var(--text-muted)]"
            }`}
            onClick={() => { setIsLogin(true); setError(""); }}
          >
            Đăng nhập
          </button>
          <button
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
              !isLogin ? "bg-[var(--bg-tertiary)] text-[var(--text-primary)] shadow-sm" : "text-[var(--text-muted)]"
            }`}
            onClick={() => { setIsLogin(false); setError(""); }}
          >
            Đăng ký
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div className="grid grid-cols-2 gap-3">
              <input
                className="input-field"
                placeholder="Họ"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
              <input
                className="input-field"
                placeholder="Tên"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
          )}

          <input
            className="input-field"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <div className="relative">
            <input
              className="input-field pr-10"
              type={showPassword ? "text" : "password"}
              placeholder="Mật khẩu"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {error && (
            <p className="text-sm text-[var(--danger)] bg-red-500/10 px-3 py-2 rounded-md">{error}</p>
          )}

          <button type="submit" className="btn-primary w-full justify-center py-3" disabled={loading}>
            {loading ? "Đang xử lý..." : isLogin ? "Đăng nhập" : "Đăng ký"}
          </button>
        </form>
      </div>
    </div>
  );
}
