"use client";

import type { ReactNode } from "react";
import { CopilotKit } from "@copilotkit/react-core/v2";
import "@copilotkit/react-core/v2/styles.css";

import { AGENT_ID, COPILOT_RUNTIME_BASE_PATH } from "../lib/constants";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <CopilotKit runtimeUrl={COPILOT_RUNTIME_BASE_PATH} agent={AGENT_ID}>
      {children}
    </CopilotKit>
  );
}
