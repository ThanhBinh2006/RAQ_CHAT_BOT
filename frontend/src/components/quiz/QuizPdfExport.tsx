"use client";

import { useState } from "react";
import { QuizQuestion } from "@/lib/api";
import { Download, X, Printer, Loader2 } from "lucide-react";

interface Props {
  quizId: string;
  title: string;
  questions: QuizQuestion[];
  onClose: () => void;
}

// Memory cache for font base64 strings so subsequent exports are instantaneous
let cachedRegular: string | null = null;
let cachedBold: string | null = null;

async function fetchFontAsBase64(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Không thể tải font từ ${url}`);
  const blob = await res.blob();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.split(",")[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function getFonts() {
  if (!cachedRegular || !cachedBold) {
    const [reg, bold] = await Promise.all([
      fetchFontAsBase64("/fonts/Arial-Regular.ttf"),
      fetchFontAsBase64("/fonts/Arial-Bold.ttf"),
    ]);
    cachedRegular = reg;
    cachedBold = bold;
  }
  return { regular: cachedRegular, bold: cachedBold };
}

export function QuizPdfExport({ quizId, title, questions, onClose }: Props) {
  const [exporting, setExporting] = useState<"student" | "teacher" | null>(null);

  const generatePdf = async (mode: "student" | "teacher") => {
    setExporting(mode);
    try {
      // Dynamic import jsPDF to avoid SSR issues
      const { jsPDF } = await import("jspdf");

      const doc = new jsPDF("p", "mm", "a4");
      const pageWidth = doc.internal.pageSize.getWidth();
      const margin = 15;
      const contentWidth = pageWidth - margin * 2;
      let y = 20;

      // Register Unicode TTF font for complete Vietnamese diacritics support
      let fontName = "helvetica";
      try {
        const { regular, bold } = await getFonts();
        doc.addFileToVFS("Arial-Regular.ttf", regular);
        doc.addFont("Arial-Regular.ttf", "Arial", "normal");

        doc.addFileToVFS("Arial-Bold.ttf", bold);
        doc.addFont("Arial-Bold.ttf", "Arial", "bold");

        fontName = "Arial";
      } catch (fontErr) {
        console.warn("Could not load custom Arial font, falling back to default:", fontErr);
      }

      // Title
      doc.setFont(fontName, "bold");
      doc.setFontSize(16);
      doc.text(title || "Đề ôn tập", pageWidth / 2, y, { align: "center" });
      y += 8;

      // Subtitle
      doc.setFont(fontName, "normal");
      doc.setFontSize(10);
      const subtitle =
        mode === "student"
          ? `Đề thi trắc nghiệm — ${questions.length} câu`
          : `Đáp án chi tiết — ${questions.length} câu`;
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
        doc.setFont(fontName, "bold");
        const qText = `Câu ${i + 1}: ${q.question_text}`;
        const qLines = doc.splitTextToSize(qText, contentWidth);
        doc.text(qLines, margin, y);
        y += qLines.length * 5 + 2;

        // Options
        doc.setFont(fontName, "normal");
        const options = [
          { letter: "A", text: q.option_a },
          { letter: "B", text: q.option_b },
          { letter: "C", text: q.option_c },
          { letter: "D", text: q.option_d },
        ];

        for (const opt of options) {
          const isCorrect = q.correct_answer === opt.letter;
          const prefix = mode === "teacher" && isCorrect ? `[✓] ${opt.letter}.` : `     ${opt.letter}.`;
          const optText = `${prefix} ${opt.text}`;
          const optLines = doc.splitTextToSize(optText, contentWidth - 5);

          if (mode === "teacher" && isCorrect) {
            doc.setFont(fontName, "bold");
          }

          doc.text(optLines, margin + 5, y);
          y += optLines.length * 5;

          if (mode === "teacher" && isCorrect) {
            doc.setFont(fontName, "normal");
          }
        }

        // Explanation (teacher mode only)
        if (mode === "teacher" && q.explanation) {
          y += 2;
          doc.setFontSize(9.5);
          doc.setFont(fontName, "normal");
          const expText = `💡 Giải thích: ${q.explanation}`;
          const expLines = doc.splitTextToSize(expText, contentWidth - 10);
          doc.text(expLines, margin + 5, y);
          y += expLines.length * 4.5 + 2;
          doc.setFontSize(11);
        }

        y += 4;
      }

      // Save file
      const safeTitle = (title || "De_on_tap").replace(/[\/\\:*?"<>|]/g, "_");
      const fileName = mode === "student" ? `${safeTitle}_De_thi.pdf` : `${safeTitle}_Dap_an.pdf`;
      doc.save(fileName);
    } catch (e: any) {
      console.error("Lỗi xuất PDF:", e);
      alert(`Xuất PDF thất bại: ${e.message || e}`);
    } finally {
      setExporting(null);
    }
  };

  // Browser-native high-res print to PDF
  const printQuiz = (mode: "student" | "teacher") => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      alert("Vui lòng cho phép mở popup trình duyệt để xem và in đề thi.");
      return;
    }

    const html = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${title || "Đề thi"} - ${mode === "student" ? "Đề thi" : "Đáp án"}</title>
          <meta charset="utf-8" />
          <style>
            body {
              font-family: 'Times New Roman', Times, serif;
              padding: 30px 40px;
              color: #111827;
              line-height: 1.6;
              font-size: 13pt;
            }
            h1 {
              text-align: center;
              font-size: 17pt;
              margin-bottom: 4px;
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }
            .subtitle {
              text-align: center;
              font-size: 11pt;
              font-style: italic;
              color: #4b5563;
              margin-bottom: 25px;
            }
            .question {
              margin-bottom: 18px;
              page-break-inside: avoid;
            }
            .q-title {
              font-weight: bold;
              margin-bottom: 6px;
            }
            .options {
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 6px 20px;
              margin-left: 12px;
            }
            .option {
              font-size: 12.5pt;
            }
            .correct {
              font-weight: bold;
              color: #166534;
            }
            .explanation {
              margin-top: 6px;
              margin-left: 12px;
              font-size: 11pt;
              font-style: italic;
              color: #4b5563;
              background: #f9fafb;
              padding: 6px 10px;
              border-radius: 4px;
              border-left: 3px solid #6366f1;
            }
            @media print {
              body { padding: 10mm; }
              @page { size: A4; margin: 12mm; }
            }
          </style>
        </head>
        <body>
          <h1>${title || "Đề ôn tập trắc nghiệm"}</h1>
          <div class="subtitle">
            ${mode === "student" ? `Đề thi trắc nghiệm — ${questions.length} câu` : `Đáp án chi tiết — ${questions.length} câu`}
          </div>
          ${questions.map((q, idx) => `
            <div class="question">
              <div class="q-title">Câu ${idx + 1}: ${q.question_text}</div>
              <div class="options">
                ${(["A", "B", "C", "D"] as const).map(letter => {
                  const field = `option_${letter.toLowerCase()}` as keyof QuizQuestion;
                  const isCorrect = mode === "teacher" && q.correct_answer === letter;
                  return `
                    <div class="option ${isCorrect ? 'correct' : ''}">
                      <strong>${letter}.</strong> ${q[field]} ${isCorrect ? ' ✓' : ''}
                    </div>
                  `;
                }).join("")}
              </div>
              ${mode === "teacher" && q.explanation ? `<div class="explanation">💡 <strong>Giải thích:</strong> ${q.explanation}</div>` : ''}
            </div>
          `).join("")}
          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `;

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
      <div className="glass-card p-6 w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-base font-bold text-slate-800">Xuất & In bộ đề</h3>
            <p className="text-xs text-slate-500 mt-0.5">{title} ({questions.length} câu)</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <p className="text-xs text-slate-500 mb-4">
          Hỗ trợ tiếng Việt đầy đủ dấu 100%. Chọn định dạng và phiên bản bạn muốn xuất:
        </p>

        <div className="space-y-3">
          {/* Tải PDF - Học sinh */}
          <button
            onClick={() => generatePdf("student")}
            disabled={exporting !== null}
            className="w-full flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 transition-all text-left group cursor-pointer disabled:opacity-50"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                {exporting === "student" ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Download size={18} />
                )}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-800">Tải file PDF — Bản Đề thi (Học sinh)</p>
                <p className="text-xs text-slate-500">Chỉ bao gồm câu hỏi và 4 lựa chọn A/B/C/D</p>
              </div>
            </div>
          </button>

          {/* Tải PDF - Giáo viên */}
          <button
            onClick={() => generatePdf("teacher")}
            disabled={exporting !== null}
            className="w-full flex items-center justify-between p-3.5 rounded-xl border border-indigo-200 bg-indigo-50/50 hover:bg-indigo-50 hover:border-indigo-400 transition-all text-left group cursor-pointer disabled:opacity-50"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-sm shadow-indigo-600/30 group-hover:scale-105 transition-transform">
                {exporting === "teacher" ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Download size={18} />
                )}
              </div>
              <div>
                <p className="text-sm font-semibold text-indigo-950">Tải file PDF — Bản Đáp án (Giáo viên)</p>
                <p className="text-xs text-indigo-600/80">Kèm đánh dấu đáp án đúng [✓] và lời giải thích</p>
              </div>
            </div>
          </button>

          {/* In hoặc Lưu PDF trực tiếp bằng trình duyệt */}
          <div className="pt-2 border-t border-slate-100 flex gap-2">
            <button
              onClick={() => printQuiz("student")}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
            >
              <Printer size={14} /> In Đề thi A4
            </button>
            <button
              onClick={() => printQuiz("teacher")}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
            >
              <Printer size={14} /> In Đáp án A4
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
