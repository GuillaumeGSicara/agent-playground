"use client";

import { CopilotChat } from "@copilotkit/react-ui";

export default function Home() {
  return (
    <div style={{ height: "100vh" }}>
    <CopilotChat
      labels={{
        title: "Web Search Agent",
        placeholder: "Ask me anything, or say 'search for...' to trigger a web search",
        initial: "Hello! I'm a web search agent. How can I help you today?",
      }}
    />
    </div>
  );
}
