"use client";

import { useState } from "react";
import { quizApi, QuizQuestion } from "@/lib/api";
import { Save, Trash2, FileDown, CheckCircle, AlertCircle } from "lucide-react";
import { QuizPdfExport } from "./QuizPdfExport";

interface Props {
  libraryId: string;
  initialQuestions: QuizQuestion[];
  suggestedTitle: string;
  onClose?: () => void;
}

export function QuizEditorCard({ libraryId, initialQuestions, suggestedTitle, onClose }: Props) {
  const [title, setTitle] = useState(suggestedTitle);
  const [questions, setQuestions] = useState<QuizQuestion[]>(initialQuestions);
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPdfExport, setShowPdfExport] = useState(false);

  const updateField = (idx: number, field: keyof QuizQuestion, value: string) => {
    setQuestions((prev) =>
      prev.map((q, i) => (i === idx ? { ...q, [field]: value } : q))
    );
  };

  const removeQuestion = (idx: number) => {
    setQuestions((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const result = await quizApi.create({
        library_id: libraryId,
        title,
        questions,
        is_edited_by_user: true,
      });
      setSavedId(result.id);
    } catch (e: any) {
      setError(e.message || "Lưu quiz thất bại");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="glass-card my-4 mx-2 overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="px-5 py-3 bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border-b border-[var(--border-color)]">
        <input
          className="input-field text-sm font-semibold"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Tên bộ đề..."
        />
      </div>

      {/* Question Editor */}
      <div className="max-h-[500px] overflow-y-auto">
        {questions.map((q, idx) => (
          <div
            key={idx}
            className="px-5 py-4 border-b border-[var(--border-color)] animate-fade-in"
          >
            {/* Question Header */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[var(--accent)]">Câu {idx + 1}</span>
              <button onClick={() => removeQuestion(idx)} className="btn-danger text-xs py-1 px-2">
                <Trash2 size={12} /> Xóa
              </button>
            </div>

            {/* Question Text */}
            <textarea
              className="input-field text-sm mb-3 resize-none"
              rows={2}
              value={q.question_text}
              onChange={(e) => updateField(idx, "question_text", e.target.value)}
              placeholder="Nội dung câu hỏi..."
            />

            {/* Options */}
            <div className="space-y-2">
              {(["A", "B", "C", "D"] as const).map((letter) => {
                const field = `option_${letter.toLowerCase()}` as keyof QuizQuestion;
                const isCorrect = q.correct_answer === letter;
                return (
                  <label
                    key={letter}
                    className={`flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer transition-all ${
                      isCorrect
                        ? "bg-green-500/10 border border-green-500/30"
                        : "bg-[var(--bg-primary)] border border-[var(--border-color)] hover:border-[var(--border-hover)]"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`correct-${idx}`}
                      checked={isCorrect}
                      onChange={() => updateField(idx, "correct_answer", letter)}
                      className="accent-[var(--success)]"
                    />
                    <span className="text-xs font-bold text-[var(--text-secondary)] w-5">{letter}.</span>
                    <input
                      className="flex-1 bg-transparent text-sm text-[var(--text-primary)] outline-none"
                      value={q[field] as string}
                      onChange={(e) => updateField(idx, field, e.target.value)}
                      placeholder={`Đáp án ${letter}`}
                    />
                  </label>
                );
              })}
            </div>

            {/* Explanation */}
            <textarea
              className="input-field text-xs mt-3 resize-none"
              rows={1}
              placeholder="Giải thích đáp án (tùy chọn)..."
              value={q.explanation ?? ""}
              onChange={(e) => updateField(idx, "explanation", e.target.value)}
            />
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="px-5 py-3 border-t border-[var(--border-color)] flex items-center gap-3 flex-wrap">
        <button onClick={handleSave} disabled={saving} className="btn-primary text-xs">
          <Save size={14} /> {saving ? "Đang lưu..." : "Lưu vào Database"}
        </button>

        {onClose && (
          <button onClick={onClose} type="button" className="btn-secondary text-xs">
            Quay lại chat
          </button>
        )}

        {savedId && (
          <button onClick={() => setShowPdfExport(true)} className="btn-secondary text-xs">
            <FileDown size={14} /> Xuất PDF
          </button>
        )}

        {savedId && (
          <span className="flex items-center gap-1 text-xs text-[var(--success)]">
            <CheckCircle size={13} /> Đã lưu
          </span>
        )}

        {error && (
          <span className="flex items-center gap-1 text-xs text-[var(--danger)]">
            <AlertCircle size={13} /> {error}
          </span>
        )}
      </div>

      {/* PDF Export Modal */}
      {showPdfExport && savedId && (
        <QuizPdfExport
          quizId={savedId}
          title={title}
          questions={questions}
          onClose={() => setShowPdfExport(false)}
        />
      )}
    </div>
  );
}
