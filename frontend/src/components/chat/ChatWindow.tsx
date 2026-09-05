
import { useState, useRef, useEffect, useMemo } from "react";
import { QuizPreviewCard } from "../quiz/QuizPreviewCard";
import { QuizEditorCard } from "../quiz/QuizEditorCard";
import { MessageSquare, Send, Bot, User } from "lucide-react";
import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { AgentState } from "../../hooks/useAssistant";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("raq_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const keys = localStorage.getItem("raq_api_keys");
    const models = localStorage.getItem("raq_model_config");
    if (keys) {
      try {
        const parsed = JSON.parse(keys);
        if (parsed.gemini) headers["X-Gemini-Key"] = parsed.gemini;
        if (parsed.openai) headers["X-Openai-Key"] = parsed.openai;
        if (parsed.anthropic) headers["X-Anthropic-Key"] = parsed.anthropic;
      } catch (e) {}
    }
    if (models) {
      try {
        const parsed = JSON.parse(models);
        if (parsed.supervisor) headers["X-Supervisor-Model"] = parsed.supervisor;
        if (parsed.generator) headers["X-Generator-Model"] = parsed.generator;
        if (parsed.evaluator) headers["X-Evaluator-Model"] = parsed.evaluator;
        if (parsed.synthesizer) headers["X-Synthesizer-Model"] = parsed.synthesizer;
      } catch (e) {}
    }
  }
  return headers;
}

interface Props {
  libraryId: string;
  sessionId: string | null;
}

export function ChatWindow({ libraryId, sessionId }: Props) {
  const [input, setInput] = useState("");
  const [editing, setEditing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Vercel AI SDK useChat pointing to backend API
  const transport = useMemo(() => new TextStreamChatTransport({
    api: `${API_BASE}/api/chat`,
    body: {
      libraryId,
      sessionId,
    },
    headers: () => getHeaders(),
  }), [libraryId, sessionId]);

  const { messages, status, sendMessage, stop, error } = useChat({
    id: sessionId || undefined,
    transport,
  });

  const isLoading = status === 'submitted' || status === 'streaming';

  const handleSubmit = (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage({
      text: input,
      metadata: { libraryId, sessionId }
    });
    setInput("");
  };

  // Tự động cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Trích xuất state từ luồng dữ liệu (nếu có Quiz)
  const lastMessage = messages[messages.length - 1];
  const agentState: AgentState = (lastMessage?.metadata as any)?.agentState || {};

  if (!sessionId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 bg-[var(--copilot-kit-background-color)]">
        <div className="w-16 h-16 rounded-2xl bg-[var(--bg-tertiary)] flex items-center justify-center">
          <MessageSquare size={28} className="text-[var(--text-muted)]" />
        </div>
        <div className="text-center">
          <p className="text-[var(--copilot-kit-secondary-contrast-color)] font-medium">Chọn hoặc tạo đoạn chat</p>
          <p className="text-sm text-[var(--copilot-kit-muted-color)] mt-1">
            Hỏi đáp kiến thức hoặc tạo đề trắc nghiệm
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative bg-[var(--copilot-kit-background-color)]">
      {/* Hiển thị Quiz nếu có */}
      {agentState.quiz_draft && agentState.quiz_draft.length > 0 && (
        <div className="absolute inset-0 z-10 bg-[var(--bg-primary)] p-4 overflow-y-auto flex flex-col">
          {editing ? (
            <QuizEditorCard
              libraryId={libraryId}
              initialQuestions={agentState.quiz_draft}
              suggestedTitle={`Đề ôn tập ${new Date().toLocaleDateString("vi-VN")}`}
            />
          ) : (
            <QuizPreviewCard
              questions={agentState.quiz_draft}
              onEdit={() => setEditing(true)}
            />
          )}
        </div>
      )}

      {/* Khu vực danh sách tin nhắn */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
          <div className="text-center text-[var(--copilot-kit-muted-color)] mt-10">
            Xin chào! Tôi có thể giúp bạn tra cứu tài liệu hoặc tạo đề trắc nghiệm. Hãy hỏi tôi bất cứ điều gì!
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role !== 'user' && (
              <div className="w-8 h-8 rounded-full bg-[var(--copilot-kit-primary-color)] flex flex-shrink-0 items-center justify-center text-white">
                <Bot size={18} />
              </div>
            )}

            <div className={`max-w-[80%] rounded-2xl p-4 ${m.role === 'user'
              ? 'bg-[var(--copilot-kit-secondary-color)] text-[var(--copilot-kit-secondary-contrast-color)] rounded-tr-sm'
              : 'bg-transparent text-[var(--copilot-kit-secondary-contrast-color)]'
              }`}>
              <div className="whitespace-pre-wrap leading-relaxed">
                {m.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('\n') || ''}
              </div>
            </div>

            {m.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-[var(--copilot-kit-secondary-color)] flex flex-shrink-0 items-center justify-center text-[var(--copilot-kit-secondary-contrast-color)]">
                <User size={18} />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Khu vực nhập liệu */}
      <div className="p-4 bg-[var(--copilot-kit-background-color)] border-t border-[var(--copilot-kit-separator-color)]">
        <form
          onSubmit={handleSubmit}
          className="relative max-w-4xl mx-auto flex items-center bg-[var(--copilot-kit-secondary-color)] rounded-full px-2 py-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Hỏi về tài liệu hoặc yêu cầu tạo đề..."
            className="flex-1 bg-transparent text-[var(--copilot-kit-secondary-contrast-color)] placeholder-[var(--copilot-kit-muted-color)] border-none outline-none px-4 py-2"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !(input || '').trim()}
            className="w-10 h-10 rounded-full bg-[var(--copilot-kit-primary-color)] text-white flex items-center justify-center disabled:opacity-50 transition-colors hover:bg-opacity-90 ml-2 flex-shrink-0"
          >
            <Send size={18} />
          </button>
        </form>
        <div className="text-center mt-2 text-xs text-[var(--copilot-kit-muted-color)]">
          AI can make mistakes. Please verify important information.
        </div>
      </div>
    </div>
  );
}