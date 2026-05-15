import type { ReactNode } from "react";
import { Providers } from "./providers";

export const metadata = { title: "Web Search Agent" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body style={{ margin: 0, height: "100vh" }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
