"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { QuizPreviewCard } from "../quiz/QuizPreviewCard";
import { QuizEditorCard } from "../quiz/QuizEditorCard";
import {
  MessageSquare,
  Send,
  Bot,
  User,
  ArrowLeft,
  Sparkles,
  BookOpen,
  FileQuestion,
  Lightbulb,
} from "lucide-react";
import { useChat } from "@ai-sdk/react";
import { TextStreamChatTransport } from "ai";
import { QuizQuestion, sessionApi } from "@/lib/api";

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

interface ParsedMessage {
  cleanText: string;
  quizDraft?: QuizQuestion[] | null;
  citations?: Array<{ page_number?: number; document_id?: string }> | null;
}

function parseMessage(rawText: string): ParsedMessage {
  const startTag = "<!--METADATA_START-->";
  const endTag = "<!--METADATA_END-->";

  const startIndex = rawText.indexOf(startTag);
  if (startIndex === -1) {
    return { cleanText: rawText };
  }

  const cleanText = rawText.substring(0, startIndex).trim();
  const endIndex = rawText.indexOf(endTag, startIndex);

  if (endIndex === -1) {
    return { cleanText };
  }

  const jsonStr = rawText.substring(startIndex + startTag.length, endIndex).trim();
  try {
    const meta = JSON.parse(jsonStr);
    return {
      cleanText,
      quizDraft: meta.quiz_draft || null,
      citations: meta.citations || null,
    };
  } catch (e) {
    console.error("Failed to parse message metadata", e);
    return { cleanText };
  }
}

interface Props {
  libraryId: string;
  sessionId: string | null;
  onMessageSent?: () => void;
}

export function ChatWindow({ libraryId, sessionId, onMessageSent }: Props) {
  const [input, setInput] = useState("");
  const [editingQuiz, setEditingQuiz] = useState<QuizQuestion[] | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
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

  const { messages, status, sendMessage, stop, error, setMessages } = useChat({
    id: sessionId || undefined,
    transport,
  });

  const isLoading = status === 'submitted' || status === 'streaming';

  // Tự động tải lại lịch sử tin nhắn khi chuyển sang đoạn chat khác
  useEffect(() => {
    if (!sessionId || !libraryId) {
      setMessages([]);
      return;
    }

    let isSubscribed = true;
    setLoadingHistory(true);

    sessionApi
      .getMessages(libraryId, sessionId)
      .then((history) => {
        if (!isSubscribed) return;
        if (history && history.length > 0) {
          setMessages(
            history.map((h) => ({
              id: h.id,
              role: h.role as "user" | "assistant",
              content: h.content,
              parts: [{ type: "text" as const, text: h.content }],
              createdAt: new Date(h.created_at),
            }))
          );
        } else {
          setMessages([]);
        }
      })
      .catch((err) => {
        console.error("Lỗi khi tải lịch sử đoạn chat:", err);
      })
      .finally(() => {
        if (isSubscribed) setLoadingHistory(false);
      });

    return () => {
      isSubscribed = false;
    };
  }, [sessionId, libraryId, setMessages]);

  const handleSubmit = (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage({
      text: input,
      metadata: { libraryId, sessionId }
    });
    setInput("");
    if (onMessageSent) {
      setTimeout(onMessageSent, 1200);
    }
  };

  const handleSuggestionClick = (promptText: string) => {
    if (isLoading) return;
    sendMessage({
      text: promptText,
      metadata: { libraryId, sessionId }
    });
    if (onMessageSent) {
      setTimeout(onMessageSent, 1200);
    }
  };

  // Tự động cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Trạng thái chưa chọn đoạn chat nào
  if (!sessionId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center bg-gradient-to-br from-slate-50 via-indigo-50/30 to-purple-50/20 relative overflow-hidden">
        {/* Background glow orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-200/30 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-200/30 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center max-w-md">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-xl shadow-indigo-500/20 mb-6 ring-4 ring-white">
            <MessageSquare size={36} className="text-white" />
          </div>
          <h2 className="text-xl font-bold text-slate-800 mb-2">Chọn hoặc tạo cuộc trò chuyện</h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            Chọn một đoạn chat ở danh sách bên trái hoặc bấm <span className="font-semibold text-indigo-600">+ Chat mới</span> để bắt đầu hỏi đáp kiến thức và tạo đề trắc nghiệm.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative bg-gradient-to-b from-slate-50/80 via-white to-slate-50/90">
      {/* Subtle background decorative grid pattern & ambient gradients */}
      <div className="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:24px_24px] opacity-70 pointer-events-none" />
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-indigo-100/40 via-purple-100/20 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-16 left-0 w-[400px] h-[400px] bg-gradient-to-tr from-sky-100/40 via-indigo-100/20 to-transparent rounded-full blur-3xl pointer-events-none" />

      {/* Editor Modal/Overlay khi nhấn 'Chỉnh sửa & Lưu' */}
      {editingQuiz && (
        <div className="absolute inset-0 z-30 bg-slate-900/40 backdrop-blur-sm p-4 md:p-6 overflow-y-auto flex flex-col animate-fade-in">
          <div className="max-w-4xl mx-auto w-full my-auto bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/80">
              <button
                onClick={() => setEditingQuiz(null)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-200/70 transition-all cursor-pointer"
              >
                <ArrowLeft size={15} /> Quay lại cuộc trò chuyện
              </button>
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-indigo-600" />
                <span className="text-sm font-bold text-slate-800">
                  Chỉnh sửa & Lưu bộ đề trắc nghiệm
                </span>
              </div>
              <div className="w-20" />
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              <QuizEditorCard
                libraryId={libraryId}
                initialQuestions={editingQuiz}
                suggestedTitle={`Đề ôn tập ${new Date().toLocaleDateString("vi-VN")}`}
                onClose={() => setEditingQuiz(null)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Khu vực danh sách tin nhắn */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 relative z-10">
        {messages.length === 0 && (
          loadingHistory ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-500">
              <div className="w-10 h-10 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-sm font-medium">Đang tải lịch sử cuộc trò chuyện...</p>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto py-12 px-4 text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center mx-auto mb-5 shadow-lg shadow-indigo-500/25 ring-4 ring-indigo-50">
                <Sparkles size={30} />
              </div>
              <h3 className="text-2xl font-bold bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-800 bg-clip-text text-transparent mb-2">
                Trợ lý Học tập & Ôn thi Thông minh
              </h3>
              <p className="text-sm text-slate-500 mb-8 max-w-md mx-auto leading-relaxed">
                Tôi có thể trả lời mọi câu hỏi bám sát tài liệu trong Thư viện, tóm tắt kiến thức hoặc tạo đề ôn tập trắc nghiệm tức thì cho bạn.
              </p>

              {/* Suggestions Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-left">
                <button
                  onClick={() => handleSuggestionClick("Tạo cho tôi bộ đề trắc nghiệm 5 câu ôn tập từ tài liệu này")}
                  className="p-4 rounded-2xl bg-white/90 hover:bg-white border border-slate-200/80 hover:border-indigo-300 shadow-sm hover:shadow-md hover:shadow-indigo-500/5 transition-all group cursor-pointer"
                >
                  <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                    <FileQuestion size={18} />
                  </div>
                  <div className="text-xs font-bold text-slate-800 mb-1">Tạo đề ôn tập 5 câu</div>
                  <div className="text-[11px] text-slate-500 line-clamp-2">Sinh câu hỏi 4 đáp án bám sát nội dung tài liệu</div>
                </button>

                <button
                  onClick={() => handleSuggestionClick("Tóm tắt các kiến thức cốt lõi và quan trọng nhất trong tài liệu")}
                  className="p-4 rounded-2xl bg-white/90 hover:bg-white border border-slate-200/80 hover:border-indigo-300 shadow-sm hover:shadow-md hover:shadow-indigo-500/5 transition-all group cursor-pointer"
                >
                  <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                    <BookOpen size={18} />
                  </div>
                  <div className="text-xs font-bold text-slate-800 mb-1">Tóm tắt tài liệu</div>
                  <div className="text-[11px] text-slate-500 line-clamp-2">Tổng hợp nhanh các luận điểm và nội dung then chốt</div>
                </button>

                <button
                  onClick={() => handleSuggestionClick("Giải thích chi tiết các thuật ngữ và khái niệm quan trọng nhất")}
                  className="p-4 rounded-2xl bg-white/90 hover:bg-white border border-slate-200/80 hover:border-indigo-300 shadow-sm hover:shadow-md hover:shadow-indigo-500/5 transition-all group cursor-pointer"
                >
                  <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                    <Lightbulb size={18} />
                  </div>
                  <div className="text-xs font-bold text-slate-800 mb-1">Giải thích khái niệm</div>
                  <div className="text-[11px] text-slate-500 line-clamp-2">Làm rõ định nghĩa kèm ví dụ minh họa dễ hiểu</div>
                </button>
              </div>
            </div>
          )
        )}

        {messages.map((m) => {
          const rawText =
            m.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('\n') ||
            (m as any).content ||
            '';
          const { cleanText, quizDraft, citations } = parseMessage(rawText);

          return (
            <div
              key={m.id}
              className={`flex flex-col gap-2 ${m.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}
            >
              <div
                className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {/* Assistant Avatar */}
                {m.role !== 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 flex flex-shrink-0 items-center justify-center text-white shadow-md shadow-indigo-500/20 ring-2 ring-white">
                    <Bot size={16} />
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`rounded-2xl px-5 py-3.5 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-tr-xs shadow-md shadow-indigo-600/15 font-normal'
                      : 'bg-white/95 backdrop-blur-md text-slate-800 border border-slate-200/80 rounded-tl-xs shadow-sm'
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed select-text">
                    {cleanText}
                  </div>

                  {/* Hiển thị Citations nếu có */}
                  {citations && citations.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-2.5 border-t border-slate-100">
                      <span className="text-[11px] font-semibold text-slate-400 mr-1">Nguồn tham khảo:</span>
                      {citations.map((c, i) => (
                        <span
                          key={i}
                          className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-50/90 text-indigo-700 border border-indigo-200/80 font-medium inline-flex items-center gap-1"
                        >
                          📄 Trang {c.page_number ?? "N/A"}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* User Avatar */}
                {m.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-slate-700 to-slate-900 flex flex-shrink-0 items-center justify-center text-white shadow-sm ring-2 ring-white">
                    <User size={16} />
                  </div>
                )}
              </div>

              {/* Hiển thị Quiz Preview Card nếu tin nhắn có quiz_draft */}
              {quizDraft && quizDraft.length > 0 && (
                <div className="w-full max-w-2xl pl-11">
                  <QuizPreviewCard
                    questions={quizDraft}
                    onEdit={() => setEditingQuiz(quizDraft)}
                  />
                </div>
              )}
            </div>
          );
        })}

        {/* Hiệu ứng chờ trả lời (AI Thinking / Processing Indicator) */}
        {isLoading && (
          <div className="flex items-start gap-3 animate-fade-in">
            <div className="relative flex items-center justify-center">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 ring-2 ring-white">
                <Bot size={16} />
              </div>
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
              </span>
            </div>

            <div className="bg-white/95 backdrop-blur-md border border-indigo-100 rounded-2xl rounded-tl-xs px-5 py-3.5 shadow-sm shadow-indigo-100/50 flex flex-col gap-2 min-w-[220px]">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-indigo-600 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 rounded-full bg-indigo-600 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 rounded-full bg-indigo-600 animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
                <span className="text-xs font-medium text-slate-600 animate-pulse">
                  AI đang suy nghĩ & xử lý...
                </span>
              </div>
              <p className="text-[11px] text-slate-400 italic">
                Đang đối chiếu dữ liệu tài liệu thư viện...
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Khu vực nhập liệu (Bottom Floating Input Bar) */}
      <div className="p-4 md:p-5 relative z-20 bg-gradient-to-t from-white via-white/90 to-transparent">
        <form
          onSubmit={handleSubmit}
          className="relative max-w-4xl mx-auto flex items-center bg-white/95 backdrop-blur-xl rounded-2xl border border-slate-200/90 shadow-lg shadow-slate-200/50 hover:border-slate-300 focus-within:border-indigo-500 focus-within:ring-4 focus-within:ring-indigo-500/10 transition-all p-1.5"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Nhập câu hỏi về tài liệu hoặc yêu cầu tạo đề thi..."
            className="flex-1 bg-transparent text-slate-800 placeholder-slate-400 border-none outline-none px-4 py-2 text-sm"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !(input || '').trim()}
            className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center disabled:opacity-40 transition-all hover:scale-105 active:scale-95 disabled:hover:scale-100 shadow-md shadow-indigo-600/20 cursor-pointer flex-shrink-0"
          >
            <Send size={16} />
          </button>
        </form>
        <div className="text-center mt-2.5 text-[11px] text-slate-400">
          Trợ lý AI bám sát tài liệu của bạn • Thông tin được đối chiếu theo từng trang
        </div>
      </div>
    </div>
  );
}