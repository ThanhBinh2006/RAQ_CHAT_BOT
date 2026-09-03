"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

// ── Types ────────────────────────────────────────────────────
export interface ApiKeys {
  nvidia?: string;
  gemini?: string;
  groq?: string;
  openai?: string;
  anthropic?: string;
}

export interface ModelConfig {
  supervisor: string;
  generator: string;
  evaluator: string;
  synthesizer: string;
}

export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  apiKeys: ApiKeys;
  modelConfig: ModelConfig;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, firstName?: string, lastName?: string) => Promise<void>;
  logout: () => void;
  setApiKeys: (keys: ApiKeys) => void;
  setModelConfig: (config: ModelConfig) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// ── Default model config ────────────────────────────────────
const DEFAULT_MODEL_CONFIG: ModelConfig = {
  supervisor: "deepseek-ai/deepseek-v4-pro-0813",
  generator: "deepseek-ai/deepseek-v4-pro-0813",
  evaluator: "deepseek-ai/deepseek-v4-pro-0813",
  synthesizer: "deepseek-ai/deepseek-v4-pro-0813",
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Provider ────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [apiKeys, setApiKeysState] = useState<ApiKeys>({});
  const [modelConfig, setModelConfigState] = useState<ModelConfig>(DEFAULT_MODEL_CONFIG);

  // Load from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("raq_token");
    const savedUser = localStorage.getItem("raq_user");
    const savedKeys = localStorage.getItem("raq_api_keys");
    const savedModels = localStorage.getItem("raq_model_config");

    if (savedToken) setToken(savedToken);
    if (savedUser) setUser(JSON.parse(savedUser));
    if (savedKeys) setApiKeysState(JSON.parse(savedKeys));
    if (savedModels) setModelConfigState(JSON.parse(savedModels));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Đăng nhập thất bại");
    }
    const data = await res.json();
    setToken(data.access_token);
    localStorage.setItem("raq_token", data.access_token);

    // Decode JWT to get user info (simple base64 decode)
    const payload = JSON.parse(atob(data.access_token.split(".")[1]));
    const userObj: User = { id: payload.sub, email };
    setUser(userObj);
    localStorage.setItem("raq_user", JSON.stringify(userObj));
  };

  const register = async (email: string, password: string, firstName?: string, lastName?: string) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, first_name: firstName, last_name: lastName }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Đăng ký thất bại");
    }
    // Auto login after register
    await login(email, password);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("raq_token");
    localStorage.removeItem("raq_user");
  };

  const setApiKeys = (keys: ApiKeys) => {
    setApiKeysState(keys);
    localStorage.setItem("raq_api_keys", JSON.stringify(keys));
  };

  const setModelConfig = (config: ModelConfig) => {
    setModelConfigState(config);
    localStorage.setItem("raq_model_config", JSON.stringify(config));
  };

  return (
    <AuthContext.Provider
      value={{ user, token, apiKeys, modelConfig, login, register, logout, setApiKeys, setModelConfig }}
    >
      {children}
    </AuthContext.Provider>
  );
}
