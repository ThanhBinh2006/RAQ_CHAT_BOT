"use client";

import { CopilotKit } from "@copilotkit/react-core/v2";
import { AuthProvider } from "@/lib/auth-context";
import { ReactNode } from "react";

const COPILOT_RUNTIME_URL = "/api/copilotkit";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <CopilotKit runtimeUrl={COPILOT_RUNTIME_URL}>
        {children}
      </CopilotKit>
    </AuthProvider>
  );
}
