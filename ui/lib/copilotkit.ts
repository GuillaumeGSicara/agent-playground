import { CopilotRuntime, createCopilotRuntimeHandler } from "@copilotkit/runtime/v2";
import { HttpAgent } from "@ag-ui/client";

import { AGENT_ID, COPILOT_RUNTIME_BASE_PATH } from "./constants";

const agentUrl: string = process.env.AGENT_URL ?? "http://localhost:8000";

const runtime: CopilotRuntime = new CopilotRuntime({
  agents: {
    [AGENT_ID]: new HttpAgent({ url: `${agentUrl}/invocations` }),
  },
});

export const copilotHandler = createCopilotRuntimeHandler({
  runtime,
  basePath: COPILOT_RUNTIME_BASE_PATH,
});
