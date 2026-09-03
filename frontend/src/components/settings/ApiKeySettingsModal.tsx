"use client";

import { useState } from "react";
import { useAuth, ApiKeys, ModelConfig } from "@/lib/auth-context";
import { X, Key, Cpu, Check } from "lucide-react";

interface Props {
  onClose: () => void;
}

// Available models per provider
const PROVIDER_MODELS: Record<string, { name: string; models: string[] }> = {
  nvidia: {
    name: "NVIDIA NIM",
    models: ["deepseek-ai/deepseek-v4-pro-0813"],
  },
  gemini: {
    name: "Google Gemini",
    models: ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b"],
  },
  groq: {
    name: "Groq Cloud",
    models: ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
  },
  openai: {
    name: "OpenAI",
    models: ["gpt-4o", "gpt-4o-mini"],
  },
  anthropic: {
    name: "Anthropic",
    models: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
  },
};

const ROLES = [
  { key: "supervisor", label: "Chatbot Supervisor", desc: "Agent chính điều phối" },
  { key: "generator", label: "Generator", desc: "Sinh câu hỏi nháp" },
  { key: "evaluator", label: "Evaluator", desc: "Kiểm duyệt chất lượng" },
  { key: "synthesizer", label: "Synthesizer", desc: "Chuẩn hóa output" },
] as const;

export function ApiKeySettingsModal({ onClose }: Props) {
  const { apiKeys, modelConfig, setApiKeys, setModelConfig } = useAuth();
  const [keys, setKeys] = useState<ApiKeys>({ ...apiKeys });
  const [models, setModels] = useState<ModelConfig>({ ...modelConfig });
  const [saved, setSaved] = useState(false);

  // Get all available models based on which keys are provided
  const availableModels: string[] = [];
  for (const [provider, config] of Object.entries(PROVIDER_MODELS)) {
    if (keys[provider as keyof ApiKeys]) {
      availableModels.push(...config.models);
    }
  }
  // Always include current selections
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
          {/* API Keys Section */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Key size={16} className="text-[var(--accent)]" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">API Keys (BYOK)</h3>
            </div>
            <p className="text-xs text-[var(--text-muted)] mb-4">
              Nhập API key để kích hoạt model tương ứng. Key được lưu trên trình duyệt, không gửi lên server.
            </p>

            <div className="space-y-3">
              {Object.entries(PROVIDER_MODELS).map(([provider, config]) => (
                <div key={provider}>
                  <label className="text-xs font-medium text-[var(--text-secondary)] mb-1 block">
                    {config.name}
                    {keys[provider as keyof ApiKeys] && (
                      <span className="ml-2 text-[var(--success)]">✓ Đã nhập</span>
                    )}
                  </label>
                  <input
                    className="input-field text-sm"
                    type="password"
                    placeholder={`Nhập ${config.name} API Key...`}
                    value={keys[provider as keyof ApiKeys] || ""}
                    onChange={(e) => setKeys({ ...keys, [provider]: e.target.value || undefined })}
                  />
                  {keys[provider as keyof ApiKeys] && (
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      Models: {config.models.join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Model Assignment Section */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Cpu size={16} className="text-[var(--accent)]" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">Phân bổ Model</h3>
            </div>
            <p className="text-xs text-[var(--text-muted)] mb-4">
              Gán model riêng cho từng vai trò. Cần có API key tương ứng.
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
                    {availableModels.length > 0 ? (
                      availableModels.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))
                    ) : (
                      <option value={models[key]}>{models[key]} (nhập key để xem thêm)</option>
                    )}
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
