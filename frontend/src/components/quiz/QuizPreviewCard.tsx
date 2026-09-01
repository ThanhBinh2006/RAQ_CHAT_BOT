"use client";

import { QuizQuestion } from "@/lib/api";
import { Eye, Edit3, CheckCircle } from "lucide-react";

interface Props {
  questions: QuizQuestion[];
  onEdit: () => void;
}

export function QuizPreviewCard({ questions, onEdit }: Props) {
  return (
    <div className="glass-card my-4 mx-2 overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          <Eye size={16} className="text-[var(--accent)]" />
          <span className="text-sm font-semibold text-[var(--text-primary)]">
            Đề trắc nghiệm — {questions.length} câu
          </span>
        </div>
        <button onClick={onEdit} className="btn-primary text-xs py-1.5 px-3">
          <Edit3 size={13} /> Chỉnh sửa & Lưu
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
                    className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-md ${
                      isCorrect
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
      </div>
    </div>
  );
}
