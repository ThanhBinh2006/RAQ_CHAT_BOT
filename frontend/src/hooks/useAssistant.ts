"use client";

// Import useAgent thay vì useCoAgent
import { useAgent } from "@copilotkit/react-core/v2";

export interface AgentState {
  messages: unknown[];
  user_id: string;
  library_id: string;
  session_id: string;
  model_config: {
    supervisor: string;
    generator: string;
    evaluator: string;
    synthesizer: string;
  };
  api_keys: Record<string, string>;
  citations: Array<{ page_number?: number; document_id?: string }> | null;
  quiz_draft: Array<{
    question_text: string;
    option_a: string;
    option_b: string;
    option_c: string;
    option_d: string;
    correct_answer: "A" | "B" | "C" | "D";
    explanation?: string;
    source_page?: number;
  }> | null;
}

export function useAssistant() {
  // Cú pháp chính xác của v2 useAgent sử dụng 'agentId'
  const { agent } = useAgent({
    agentId: "assistant"
  });

  return agent;
}
