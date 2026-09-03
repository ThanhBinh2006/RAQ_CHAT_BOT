
import { useState, useRef, useEffect } from "react";
import { QuizPreviewCard } from "../quiz/QuizPreviewCard";
import { QuizEditorCard } from "../quiz/QuizEditorCard";
import { MessageSquare, Send, Bot, User } from "lucide-react";
import { useChat } from "@ai-sdk/react";
import { AgentState } from "../../hooks/useAssistant";

interface Props {
  libraryId: string;
  sessionId: string | null;
}

export function ChatWindow({ libraryId, sessionId }: Props) {
  const [editing, setEditing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Vercel AI SDK useChat
  const { messages, input, setInput, handleSubmit, isLoading, data } = useChat({
    api: "/api/chat",
    // Pass a function to dynamically evaluate props on submission
    body: () => ({
      libraryId,
      sessionId,
    }),
  });


  // Tự động cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Trích xuất state từ luồng dữ liệu (nếu có Quiz)
  const agentState: AgentState = (data as any)?.[data?.length - 1] || {};

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
              <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
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
            disabled={isLoading || !input.trim()}
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