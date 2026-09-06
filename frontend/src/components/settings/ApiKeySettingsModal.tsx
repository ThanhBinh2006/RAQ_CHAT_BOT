"use client";

import { useState } from "react";
import { useAuth, ApiKeys, ModelConfig } from "@/lib/auth-context";
import { X, Key, Cpu, Check, ShieldCheck } from "lucide-react";

interface Props {
  onClose: () => void;
}

// Default models provided by system (no user API key required)
const SYSTEM_MODELS = [
  "deepseek-ai/deepseek-v4-pro-0813",
  "deepseek-ai/deepseek-v4-flash-0731",
];

// BYOK Providers that users are allowed to configure
const BYOK_PROVIDERS: Record<string, { name: string; placeholder: string; models: string[] }> = {
  gemini: {
    name: "Google Gemini",
    placeholder: "Nhập Gemini API Key (AIzaSy...)",
    models: ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-3.5-flash", "gemma-4-31B"],
  },
  openai: {
    name: "OpenAI / ChatGPT",
    placeholder: "Nhập OpenAI API Key (sk-...)",
    models: ["gpt-4o", "gpt-4o-mini"],
  },
  anthropic: {
    name: "Anthropic / Claude",
    placeholder: "Nhập Anthropic API Key (sk-ant-...)",
    models: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
  },
};

const ROLES = [
  { key: "supervisor", label: "Chatbot Supervisor", desc: "Agent chính điều phối" },
  { key: "generator", label: "Generator", desc: "Sinh câu hỏi nháp" },
  { key: "evaluator", label: "Evaluator", desc: "Kiểm duyệt chất lượng" },
  { key: "synthesizer", label: "Synthesizer", desc: "Chuẩn hóa & tạo lại câu hỏi" },
] as const;

export function ApiKeySettingsModal({ onClose }: Props) {
  const { apiKeys, modelConfig, setApiKeys, setModelConfig } = useAuth();
  const [keys, setKeys] = useState<ApiKeys>({
    gemini: apiKeys.gemini,
    openai: apiKeys.openai,
    anthropic: apiKeys.anthropic,
  });
  const [models, setModels] = useState<ModelConfig>({ ...modelConfig });
  const [saved, setSaved] = useState(false);

  // Available models: System default models are always available + unlocked BYOK models
  const availableModels: string[] = [...SYSTEM_MODELS];
  for (const [provider, config] of Object.entries(BYOK_PROVIDERS)) {
    if (keys[provider as keyof ApiKeys]) {
      availableModels.push(...config.models);
    }
  }

  // Ensure currently selected models are included
  Object.values(models).forEach((m) => {
    if (m && !availableModels.includes(m)) availableModels.push(m);
  });

  const handleSave = () => {
    setApiKeys(keys);
    setModelConfig(models);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-card w-full max-w-lg max-h-[85vh] overflow-y-auto animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-color)] sticky top-0 bg-[var(--bg-secondary)] z-10">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Cài đặt API & Model</h2>
          <button onClick={onClose} className="p-1 hover:bg-[var(--bg-hover)] rounded">
            <X size={18} className="text-[var(--text-muted)]" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* System Default & Embedding Info Box */}
          <div className="p-3 bg-[var(--bg-card)] rounded-lg border border-[var(--border-color)] text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-[var(--accent)]">
              <ShieldCheck size={15} />
              <span>Cấu hình Mặc định & Vector Embedding (Hệ thống quản lý)</span>
            </div>
            <p className="text-[var(--text-muted)]">
              Hệ thống đã tích hợp sẵn model <strong>DeepSeek V4</strong> và công cụ trích xuất vector <strong>Embedding 2048</strong> qua server backend. Bạn có thể sử dụng ngay lập tức mà không cần cung cấp API key.
            </p>
          </div>

          {/* BYOK API Keys Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Key size={16} className="text-[var(--accent)]" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Tùy chọn API Key (BYOK)</h3>
            </div>
            <p className="text-xs text-[var(--text-muted)] mb-4">
              Chỉ hỗ trợ mở rộng qua <strong>Gemini</strong>, <strong>ChatGPT (OpenAI)</strong> hoặc <strong>Claude (Anthropic)</strong>. Key được lưu bảo mật trên trình duyệt của bạn.
            </p>

            <div className="space-y-3">
              {Object.entries(BYOK_PROVIDERS).map(([provider, config]) => (
                <div key={provider}>
                  <label className="text-xs font-medium text-[var(--text-secondary)] mb-1 block">
                    {config.name}
                    {keys[provider as keyof ApiKeys] && (
                      <span className="ml-2 text-[var(--success)]">✓ Đã kích hoạt</span>
                    )}
                  </label>
                  <input
                    className="input-field text-sm"
                    type="password"
                    placeholder={config.placeholder}
                    value={keys[provider as keyof ApiKeys] || ""}
                    onChange={(e) => setKeys({ ...keys, [provider]: e.target.value || undefined })}
                  />
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Models mở khóa: {config.models.join(", ")}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Model Assignment Section */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Cpu size={16} className="text-[var(--accent)]" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Phân bổ Model cho từng vai trò</h3>
            </div>
            <p className="text-xs text-[var(--text-muted)] mb-4">
              Chọn model xử lý cho từng vai trò trong hệ thống Multi-Agent:
            </p>

            <div className="space-y-3">
              {ROLES.map(({ key, label, desc }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-[var(--text-secondary)] mb-1 block">
                    {label}{" "}
                    <span className="text-[var(--text-muted)] font-normal">— {desc}</span>
                  </label>
                  <select
                    className="input-field text-sm"
                    value={models[key]}
                    onChange={(e) => setModels({ ...models, [key]: e.target.value })}
                  >
                    {availableModels.map((m) => (
                      <option key={m} value={m}>
                        {m} {SYSTEM_MODELS.includes(m) ? "(Mặc định - Miễn phí)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--border-color)] flex items-center justify-between sticky bottom-0 bg-[var(--bg-secondary)]">
          <button onClick={onClose} className="btn-secondary">
            Đóng
          </button>
          <button onClick={handleSave} className="btn-primary">
            {saved ? (
              <><Check size={14} /> Đã lưu!</>
            ) : (
              "Lưu cài đặt"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
