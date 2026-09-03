"use client";

import { CopilotKit } from "@copilotkit/react-core/v2";
import { AuthProvider } from "@/lib/auth-context";
import { ReactNode } from "react";

const COPILOT_RUNTIME_URL =
  process.env.NEXT_PUBLIC_COPILOT_RUNTIME_URL || "http://localhost:8000/api/copilotkit";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <CopilotKit runtimeUrl={COPILOT_RUNTIME_URL} useSingleEndpoint={false}>
        {children}
      </CopilotKit>
    </AuthProvider>
  );
}
