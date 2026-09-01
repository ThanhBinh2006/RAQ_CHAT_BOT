"use client";

import { QuizQuestion } from "@/lib/api";
import { Download, X } from "lucide-react";

interface Props {
  quizId: string;
  title: string;
  questions: QuizQuestion[];
  onClose: () => void;
}

export function QuizPdfExport({ quizId, title, questions, onClose }: Props) {
  const generatePdf = async (mode: "student" | "teacher") => {
    // Dynamic import jsPDF to avoid SSR issues
    const { jsPDF } = await import("jspdf");

    const doc = new jsPDF("p", "mm", "a4");
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 15;
    const contentWidth = pageWidth - margin * 2;
    let y = 20;

    // Title
    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.text(title, pageWidth / 2, y, { align: "center" });
    y += 8;

    // Subtitle
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    const subtitle =
      mode === "student"
        ? `De thi trac nghiem - ${questions.length} cau`
        : `Dap an chi tiet - ${questions.length} cau`;
    doc.text(subtitle, pageWidth / 2, y, { align: "center" });
    y += 12;

    // Questions
    doc.setFontSize(11);
    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];

      // Check page break
      if (y > 260) {
        doc.addPage();
        y = 20;
      }

      // Question text
      doc.setFont("helvetica", "bold");
      const qText = `Cau ${i + 1}: ${q.question_text}`;
      const qLines = doc.splitTextToSize(qText, contentWidth);
      doc.text(qLines, margin, y);
      y += qLines.length * 5 + 2;

      // Options
      doc.setFont("helvetica", "normal");
      const options = [
        { letter: "A", text: q.option_a },
        { letter: "B", text: q.option_b },
        { letter: "C", text: q.option_c },
        { letter: "D", text: q.option_d },
      ];

      for (const opt of options) {
        const isCorrect = q.correct_answer === opt.letter;
        const prefix = mode === "teacher" && isCorrect ? `[V] ${opt.letter}.` : `    ${opt.letter}.`;
        const optText = `${prefix} ${opt.text}`;
        const optLines = doc.splitTextToSize(optText, contentWidth - 5);

        if (mode === "teacher" && isCorrect) {
          doc.setFont("helvetica", "bold");
        }

        doc.text(optLines, margin + 5, y);
        y += optLines.length * 5;

        if (mode === "teacher" && isCorrect) {
          doc.setFont("helvetica", "normal");
        }
      }

      // Explanation (teacher mode only)
      if (mode === "teacher" && q.explanation) {
        y += 2;
        doc.setFontSize(9);
        doc.setFont("helvetica", "italic");
        const expText = `Giai thich: ${q.explanation}`;
        const expLines = doc.splitTextToSize(expText, contentWidth - 10);
        doc.text(expLines, margin + 5, y);
        y += expLines.length * 4 + 2;
        doc.setFontSize(11);
        doc.setFont("helvetica", "normal");
      }

      y += 4;
    }

    // Save
    const fileName = mode === "student" ? `${title}_De_thi.pdf` : `${title}_Dap_an.pdf`;
    doc.save(fileName);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-card p-6 w-full max-w-sm animate-fade-in">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">Xuất PDF</h3>
          <button onClick={onClose} className="p-1 hover:bg-[var(--bg-hover)] rounded">
            <X size={18} className="text-[var(--text-muted)]" />
          </button>
        </div>

        <p className="text-sm text-[var(--text-secondary)] mb-5">
          Chọn phiên bản PDF muốn xuất:
        </p>

        <div className="space-y-3">
          <button
            onClick={() => generatePdf("student")}
            className="btn-secondary w-full justify-center py-3"
          >
            <Download size={16} />
            <div className="text-left">
              <p className="font-medium">Bản Đề thi (Học sinh)</p>
              <p className="text-xs text-[var(--text-muted)]">Chỉ câu hỏi và 4 lựa chọn</p>
            </div>
          </button>

          <button
            onClick={() => generatePdf("teacher")}
            className="btn-primary w-full justify-center py-3"
          >
            <Download size={16} />
            <div className="text-left">
              <p className="font-medium">Bản Đáp án (Giáo viên)</p>
              <p className="text-xs opacity-80">Kèm đáp án đúng và giải thích</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
