import "./globals.css";
import type { Metadata } from "next";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "SkillSentinel · Agent Builder",
  description: "Spin up a secured OpenClaw agent on your VPS — skills reviewed by SkillSentinel before install.",
};

function ClawIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M13 2L4 7V14C4 19.5 8 24.2 13 25.5C18 24.2 22 19.5 22 14V7L13 2Z"
        stroke="hsl(25,95%,53%)"
        strokeWidth="1.5"
        strokeLinejoin="round"
        fill="hsl(25,95%,53%,0.1)"
      />
      <circle cx="13" cy="13" r="3.5" stroke="hsl(25,95%,53%)" strokeWidth="1.5" />
      <circle cx="13" cy="13" r="1.2" fill="hsl(25,95%,53%)" />
    </svg>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-screen bg-background text-foreground">
            <header className="border-b border-border bg-white/80 backdrop-blur-sm sticky top-0 z-10">
              <div className="container flex h-14 items-center justify-between">
                <div className="flex items-center gap-3">
                  <ClawIcon />
                  <span className="text-base font-bold tracking-tight text-foreground">
                    Skill<span className="oc-orange">Sentinel</span>
                  </span>
                  <span className="hidden items-center gap-1.5 sm:flex">
                    <span className="h-1.5 w-1.5 rounded-full bg-[hsl(25,95%,53%)]" />
                    <span className="label-tag">OpenClaw 2026 · Agent Builder</span>
                  </span>
                </div>
                <a
                  href="https://docs.openclaw.ai"
                  target="_blank"
                  rel="noreferrer"
                  className="label-tag hover:text-foreground transition-colors"
                >
                  docs ↗
                </a>
              </div>
            </header>
            <main className="container py-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
