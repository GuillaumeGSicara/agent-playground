import { CopilotRuntime, ExperimentalEmptyAdapter, copilotRuntimeNextJSAppRouterEndpoint } from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import type { NextRequest } from "next/server";

import { AGENT_ID, COPILOT_RUNTIME_BASE_PATH } from "./constants";

const agentUrl: string = process.env.AGENT_URL ?? "http://localhost:8000";

const runtime: CopilotRuntime = new CopilotRuntime({
  agents: {
    [AGENT_ID]: new HttpAgent({ url: `${agentUrl}/invocations` }),
  },
});

const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
  runtime,
  serviceAdapter: new ExperimentalEmptyAdapter(),
  endpoint: COPILOT_RUNTIME_BASE_PATH,
});

export async function copilotHandler(req: NextRequest): Promise<Response> {
  return handleRequest(req);
}
