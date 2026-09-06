"use client";

import { QuizQuestion } from "@/lib/api";
import { Eye, Edit3, CheckCircle } from "lucide-react";

interface Props {
  questions: QuizQuestion[];
  onEdit: () => void;
  isGenerating?: boolean;
  totalTarget?: number;
}

export function QuizPreviewCard({ questions, onEdit, isGenerating, totalTarget }: Props) {
  return (
    <div className="glass-card my-4 mx-2 overflow-hidden animate-fade-in border border-indigo-200/80 shadow-md">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-indigo-500/15 via-purple-500/10 to-indigo-500/5 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          {isGenerating ? (
            <div className="relative flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <Eye size={16} className="text-[var(--accent)]" />
          )}
          <span className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
            Đề trắc nghiệm —{" "}
            {isGenerating ? (
              <span className="text-indigo-600 font-bold animate-pulse">
                Đang tạo {questions.length}
                {totalTarget ? `/${totalTarget}` : ""} câu...
              </span>
            ) : (
              <span>{questions.length} câu</span>
            )}
          </span>
          {isGenerating && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium animate-pulse hidden sm:inline-block">
              Nối từng đợt
            </span>
          )}
        </div>
        <button
          onClick={onEdit}
          disabled={isGenerating}
          className={`btn-primary text-xs py-1.5 px-3 transition-all ${isGenerating ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:scale-105"
            }`}
          title={isGenerating ? "Vui lòng đợi AI sinh xong để lưu" : "Chỉnh sửa & Lưu đề thi"}
        >
          <Edit3 size={13} /> {isGenerating ? "Đang tạo..." : "Chỉnh sửa & Lưu"}
        </button>
      </div>

      {/* Question List */}
      <div className="max-h-96 overflow-y-auto">
        {questions.map((q, idx) => (
          <div
            key={idx}
            className="px-5 py-3 border-b border-[var(--border-color)] hover:bg-[var(--bg-hover)] transition-colors"
          >
            <p className="text-sm font-medium text-[var(--text-primary)] mb-2">
              <span className="text-[var(--accent)] mr-2">Câu {idx + 1}.</span>
              {q.question_text}
            </p>
            <div className="grid grid-cols-2 gap-2">
              {(["A", "B", "C", "D"] as const).map((letter) => {
                const field = `option_${letter.toLowerCase()}` as keyof QuizQuestion;
                const isCorrect = q.correct_answer === letter;
                return (
                  <div
                    key={letter}
                    className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-md ${isCorrect
                        ? "bg-green-500/10 text-[var(--success)] border border-green-500/30"
                        : "text-[var(--text-secondary)]"
                      }`}
                  >
                    {isCorrect && <CheckCircle size={12} />}
                    <span className="font-medium">{letter}.</span>
                    <span>{q[field] as string}</span>
                  </div>
                );
              })}
            </div>
            {q.explanation && (
              <p className="text-xs text-[var(--text-muted)] mt-2 italic">💡 {q.explanation}</p>
            )}
          </div>
        ))}

        {isGenerating && (
          <div className="px-5 py-3.5 bg-indigo-50/60 flex items-center justify-center gap-2 text-xs text-indigo-700 font-medium border-t border-indigo-100/80 animate-pulse">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-600"></span>
            </span>
            <span>Đang tiếp tục biên soạn và thẩm định đợt câu hỏi tiếp theo...</span>
          </div>
        )}
      </div>
    </div>
  );
}
