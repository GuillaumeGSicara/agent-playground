"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";

export default function Home() {
  return (
    <CopilotChat
      attachments={{
        enabled: true,
        accept: "image/png,image/jpeg,application/pdf",
      }}
      labels={{
        modalHeaderTitle: "Web Search Agent",
        chatInputPlaceholder: "Ask me anything, or say 'search for...' to trigger a web search",
        welcomeMessageText: "Hello! I'm a web search agent. How can I help you today?",
      }}
    />
  );
}
