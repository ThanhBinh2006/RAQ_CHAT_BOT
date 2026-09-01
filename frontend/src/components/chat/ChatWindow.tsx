"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgentStateRender } from "@copilotkit/react-core";
import { useState } from "react";
import { QuizPreviewCard } from "../quiz/QuizPreviewCard";
import { QuizEditorCard } from "../quiz/QuizEditorCard";
import { MessageSquare } from "lucide-react";
import "@copilotkit/react-ui/styles.css";

interface Props {
  libraryId: string;
  sessionId: string | null;
}

export function ChatWindow({ libraryId, sessionId }: Props) {
  const [editing, setEditing] = useState(false);

  // Render quiz draft when it appears in agent state
  useCoAgentStateRender({
    name: "assistant",
    render: ({ state }) => {
      if (!state.quiz_draft?.length) return null;
      return editing ? (
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
      );
    },
  });

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
    <div className="flex-1 flex flex-col overflow-hidden">
      <CopilotChat
        agent="assistant"
        labels={{
          title: "Trợ lý Thư viện",
          initial: "Xin chào! Tôi có thể giúp bạn tra cứu tài liệu hoặc tạo đề trắc nghiệm. Hãy hỏi tôi bất cứ điều gì!",
          placeholder: "Hỏi về tài liệu hoặc yêu cầu tạo đề...",
        }}
        className="flex-1"
      />
    </div>
  );
}
