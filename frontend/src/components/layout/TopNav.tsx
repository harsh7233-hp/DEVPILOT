"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useSelectedRepo } from "@/lib/repo-context";
import { api } from "@/lib/api";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { BranchSelector } from "@/components/ui/BranchSelector";
import { CommandPalette } from "@/components/command/CommandPalette";
import { NotificationBell } from "@/components/notifications/NotificationBell";

export function TopNav({ onMenuClick }: { onMenuClick?: () => void }) {
  const { user, logout } = useAuth();
  const { repo, branch, setRepo, setBranch } = useSelectedRepo();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [aiStatus, setAiStatus] = useState<{ ai_configured: boolean; model: string | null } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.health
      .aiStatus()
      .then((s) => !cancelled && setAiStatus(s))
      .catch(() => !cancelled && setAiStatus({ ai_configured: false, model: null }));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <>
      <header
        className="h-11 border-b backdrop-blur-sm shrink-0 flex items-center gap-2 px-3 sm:px-4"
        style={{ borderColor: "var(--border)", background: "var(--nav-bg)" }}
      >
        {/* Mobile menu button */}
        <button
          onClick={onMenuClick}
          aria-label="Open menu"
          className="lg:hidden h-7 w-7 -ml-0.5 flex items-center justify-center rounded-md transition-colors active:bg-[var(--muted)]"
          style={{ color: "var(--foreground)" }}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>

        {/* Repository + Branch selectors */}
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <RepoSelector
            value={repo ? repo.fullName : ""}
            onChange={(o, n) => {
              api.repositories.get(o, n).then((r) => setRepo(r.repository)).catch(() => {});
            }}
            className="max-w-[180px] sm:max-w-[220px] min-w-0 [&>button]:h-7 [&>button]:text-[11px]"
          />
          {repo && (
            <BranchSelector owner={repo.owner} repo={repo.name} value={branch} onChange={setBranch} className="shrink-0 [&>button]:h-7 [&>button]:text-[11px]" />
          )}
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-1 shrink-0">
          {/* Search */}
          <button
            onClick={() => setPaletteOpen(true)}
            aria-label="Search (Command K)"
            title="Search — ⌘K"
            className="h-7 px-2 flex items-center gap-1.5 rounded-md border text-[11px] transition-colors hover:brightness-95"
            style={{ borderColor: "var(--input-border)", color: "var(--muted-foreground)", background: "var(--btn-secondary-bg)" }}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <kbd className="hidden sm:inline text-[9px] font-mono px-1 py-0.5 rounded border" style={{ borderColor: "var(--border)" }}>⌘K</kbd>
          </button>

          {/* AI status */}
          <span
            role="status"
            aria-label={aiLabel(aiStatus)}
            title={aiLabel(aiStatus)}
            className="h-7 w-7 sm:w-auto sm:px-2 flex items-center justify-center gap-1.5 rounded-md border shrink-0"
            style={{ borderColor: "var(--input-border)" }}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${aiStatus?.ai_configured ? "bg-emerald-500 dp-pulse" : "bg-zinc-400 dark:bg-zinc-600"}`} />
            <span className="hidden sm:inline text-[10px] font-medium uppercase tracking-wide" style={{ color: aiStatus?.ai_configured ? "#10b981" : "var(--muted-foreground)" }}>
              AI
            </span>
          </span>

          <NotificationBell />
          <ThemeToggle />

          {/* User */}
          {user?.avatar_url && (
            <Image src={user.avatar_url} alt={user.login} width={20} height={20} className="rounded-full shrink-0" unoptimized />
          )}
          {user ? (
            <button
              onClick={() => logout()}
              className="h-7 px-2 flex items-center justify-center text-[10px] font-medium rounded-md border transition-colors active:scale-[0.97]"
              style={{ borderColor: "var(--input-border)", color: "var(--muted-foreground)" }}
            >
              Disconnect
            </button>
          ) : (
            <a
              href={api.auth.getGithubUrl()}
              className="h-7 px-2.5 flex items-center justify-center text-[11px] font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-500 active:scale-[0.97] transition-all whitespace-nowrap"
            >
              Connect
            </a>
          )}
        </div>
      </header>

      {paletteOpen && <CommandPalette onClose={() => setPaletteOpen(false)} />}
    </>
  );
}

function aiLabel(status: { ai_configured: boolean; model: string | null } | null): string {
  if (!status) return "Checking AI availability...";
  if (!status.ai_configured) return "AI not configured (GROQ_API_KEY missing)";
  return `AI ready · ${status.model ?? "unknown model"}`;
}
