
import { CopilotChat } from "@copilotkit/react-core/v2";
import { useState } from "react";
import { QuizPreviewCard } from "../quiz/QuizPreviewCard";
import { QuizEditorCard } from "../quiz/QuizEditorCard";
import { MessageSquare } from "lucide-react";
import "@copilotkit/react-core/v2/styles.css";
import { useAssistant } from "../../hooks/useAssistant";

interface Props {
  libraryId: string;
  sessionId: string | null;
}

// 💡 Khai báo kiểu dữ liệu cho State của Agent để TypeScript kiểm soát chặt chẽ
interface AgentState {
  quiz_draft?: any[];
}

export function ChatWindow({ libraryId, sessionId }: Props) {
  const [editing, setEditing] = useState(false);

  // 💡 Sử dụng custom hook của chúng ta thay vì gọi trực tiếp
  const agent = useAssistant();

  // Ép kiểu hoặc fallback object trống để tránh lỗi undefined khi chưa đồng bộ xong
  const state = (agent?.state as AgentState) || {};

  if (!sessionId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-[var(--bg-tertiary)] flex items-center justify-center">
          <MessageSquare size={28} className="text-[var(--text-muted)]" />
        </div>
        <div className="text-center">
          <p className="text-[var(--text-secondary)] font-medium">Chọn hoặc tạo đoạn chat</p>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Hỏi đáp kiến thức hoặc tạo đề trắc nghiệm
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative">
      {/* 
        💡 V2 Generative UI logic: Nếu trong bộ nhớ Agent xuất hiện `quiz_draft`, 
        nó sẽ ngay lập tức được vẽ đè/hiển thị song song lên màn hình 
      */}
      {state.quiz_draft && state.quiz_draft.length > 0 && (
        <div className="absolute inset-0 z-10 bg-[var(--bg-primary)] p-4 overflow-y-auto flex flex-col">
          {editing ? (
            <QuizEditorCard
              libraryId={libraryId}
              initialQuestions={state.quiz_draft}
              suggestedTitle={`Đề ôn tập ${new Date().toLocaleDateString("vi-VN")}`}
            />
          ) : (
            <QuizPreviewCard
              questions={state.quiz_draft}
              onEdit={() => setEditing(true)}
            />
          )}
        </div>
      )}

      {/* Giao diện Chat chính */}
      <CopilotChat
        agentId="assistant"
        labels={{
          welcomeMessageText: "Xin chào! Tôi có thể giúp bạn tra cứu tài liệu hoặc tạo đề trắc nghiệm. Hãy hỏi tôi bất cứ điều gì!",
          chatInputPlaceholder: "Hỏi về tài liệu hoặc yêu cầu tạo đề...",
        }}
        className="flex-1"
      />
    </div>
  );
}