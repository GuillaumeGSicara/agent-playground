"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { CopilotChat } from "@copilotkit/react-core/v2";

const ThreadSidebar = dynamic(
  () => import("./thread-sidebar").then((m) => m.ThreadSidebar),
  { ssr: false, loading: () => <SidebarSkeleton /> },
);

function SidebarSkeleton() {
  return (
    <div
      style={{
        width: 260,
        minWidth: 260,
        borderRight: "1px solid #e5e7eb",
        background: "#f9fafb",
      }}
    />
  );
}

export default function Home() {
  const [activeThreadId, setActiveThreadId] = useState<string | undefined>();

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <ThreadSidebar
        activeThreadId={activeThreadId}
        onSelectThread={setActiveThreadId}
      />
      <div style={{ flex: 1, overflow: "hidden" }}>
        <CopilotChat
          attachments={{
            enabled: true,
            accept: "image/png,image/jpeg,application/pdf",
          }}
          threadId={activeThreadId}
          labels={{
            modalHeaderTitle: "Web Search Agent",
            chatInputPlaceholder: "Ask me anything, or say 'search for...' to trigger a web search",
            welcomeMessageText: "Hello! I'm a web search agent. How can I help you today?",
          }}
        />
      </div>
    </div>
  );
}
