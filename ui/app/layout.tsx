import type { ReactNode } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

export const metadata = { title: "Web Search Agent" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, height: "100vh" }}>
        <CopilotKit runtimeUrl="/api/copilotkit" agent="web_search_agent">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
