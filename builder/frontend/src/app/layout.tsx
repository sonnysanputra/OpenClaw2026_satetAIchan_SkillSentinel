import "./globals.css";
import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "OpenClaw Agent Builder",
  description: "Spin up a secured OpenClaw agent on your VPS — no terminal required.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <div className="min-h-screen bg-background text-foreground">
            <header className="border-b">
              <div className="container flex h-14 items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-lg">🦞</span>
                  <span className="font-semibold">OpenClaw Agent Builder</span>
                  <span className="text-muted-foreground">· secured by SkillsSentinel</span>
                </div>
                <a href="https://docs.openclaw.ai" target="_blank" rel="noreferrer" className="text-xs text-muted-foreground hover:underline">
                  docs ↗
                </a>
              </div>
            </header>
            <main className="container py-6">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
