"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type GitHubRepo } from "@/lib/api";
import { useSelectedRepo } from "@/lib/repo-context";

interface NavItem {
  label: string;
  hint: string;
  href: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Command Center", hint: "Repository overview", href: "/command-center" },
  { label: "Overview", hint: "Classic dashboard", href: "/dashboard" },
  { label: "Repositories", hint: "Browse & analyze", href: "/repositories" },
  { label: "Code Explorer", hint: "Files, functions, classes", href: "/code-explorer" },
  { label: "Architecture", hint: "Dependency graph", href: "/architecture" },
  { label: "Code Intelligence", hint: "Health & findings", href: "/intelligence" },
  { label: "Security", hint: "Security findings", href: "/security" },
  { label: "Pipelines", hint: "CI/CD detection", href: "/pipelines" },
  { label: "Impact Analysis", hint: "Change blast radius", href: "/impact-analysis" },
  { label: "AI Assistant", hint: "Ask your codebase", href: "/ai-assistant" },
  { label: "Code Review", hint: "Static + AI review", href: "/code-review" },
  { label: "Settings", hint: "Preferences", href: "/settings" },
];

type Row =
  | { kind: "nav"; item: NavItem }
  | { kind: "repo"; item: GitHubRepo };

export function CommandPalette({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { setRepo } = useSelectedRepo();
  const [query, setQuery] = useState("");
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [reposLoaded, setReposLoaded] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!reposLoaded) {
      api.repositories
        .list()
        .then((res) => {
          setRepos(res.repositories || []);
          setReposLoaded(true);
        })
        .catch(() => setReposLoaded(true));
    }
    inputRef.current?.focus();
  }, [reposLoaded]);

  const rows = useMemo<Row[]>(() => {
    const q = query.trim().toLowerCase();
    const navMatches = NAV_ITEMS.filter(
      (n) => !q || n.label.toLowerCase().includes(q) || n.hint.toLowerCase().includes(q)
    ).map((item) => ({ kind: "nav" as const, item }));
    const repoMatches = (
      q
        ? repos.filter(
            (r) =>
              r.full_name.toLowerCase().includes(q) ||
              r.name.toLowerCase().includes(q)
          )
        : repos
    )
      .slice(0, q ? 8 : 5)
      .map((item) => ({ kind: "repo" as const, item }));
    return [...repoMatches, ...navMatches];
  }, [query, repos]);

  // Derived, never out of bounds — no effect needed to clamp.
  const clampedIndex = rows.length === 0 ? 0 : Math.min(activeIndex, rows.length - 1);

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-index="${clampedIndex}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [clampedIndex]);

  const select = useCallback(
    (row: Row) => {
      onClose();
      if (row.kind === "repo") {
        setRepo(row.item);
        router.push("/command-center");
      } else {
        router.push(row.item.href);
      }
    },
    [onClose, setRepo, router]
  );

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[12vh] px-4"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" />
      <div
        className="relative w-full max-w-lg rounded-xl border shadow-2xl overflow-hidden dp-fade-up"
        style={{ background: "var(--card)", borderColor: "var(--border)", animationDuration: "150ms" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 px-4 border-b" style={{ borderColor: "var(--border)" }}>
          <svg className="h-4 w-4 shrink-0" style={{ color: "var(--muted-foreground)" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActiveIndex((i) => (i + 1) % Math.max(1, rows.length));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActiveIndex((i) => (i - 1 + rows.length) % Math.max(1, rows.length));
              } else if (e.key === "Enter") {
                e.preventDefault();
                const row = rows[clampedIndex];
                if (row) select(row);
              } else if (e.key === "Escape") {
                onClose();
              }
            }}
            placeholder="Search pages and repositories..."
            className="w-full h-12 bg-transparent text-sm outline-none"
            style={{ color: "var(--foreground)" }}
            autoComplete="off"
            spellCheck={false}
          />
          <kbd
            className="hidden sm:block text-[10px] font-mono px-1.5 py-0.5 rounded border shrink-0"
            style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
          >
            ESC
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[46dvh] overflow-y-auto overscroll-contain py-1.5">
          {rows.length === 0 && (
            <p className="px-4 py-8 text-center text-sm" style={{ color: "var(--muted-foreground)" }}>
              No matches
            </p>
          )}
          {rows.map((row, i) => (
            <button
              key={row.kind === "repo" ? `r-${row.item.id}` : `n-${row.item.href}`}
              data-index={i}
              onClick={() => select(row)}
              onMouseEnter={() => setActiveIndex(i)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors min-h-[44px]"
              style={{
                background:
                  i === clampedIndex ? "var(--dropdown-item-hover)" : "transparent",
              }}
            >
              {row.kind === "repo" ? (
                <>
                  <span
                    className="h-6 w-6 rounded-md flex items-center justify-center shrink-0"
                    style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                    </svg>
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium truncate" style={{ color: "var(--foreground)" }}>
                      {row.item.full_name}
                    </span>
                    <span className="block text-[11px] truncate" style={{ color: "var(--muted-foreground)" }}>
                      Repository{row.item.private ? " · private" : ""}
                    </span>
                  </span>
                </>
              ) : (
                <>
                  <span
                    className="h-6 w-6 rounded-md flex items-center justify-center shrink-0"
                    style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12l-7.5 7.5M21 12H3" />
                    </svg>
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium truncate" style={{ color: "var(--foreground)" }}>
                      {row.item.label}
                    </span>
                    <span className="block text-[11px] truncate" style={{ color: "var(--muted-foreground)" }}>
                      {row.item.hint}
                    </span>
                  </span>
                </>
              )}
              {i === clampedIndex && (
                <kbd
                  className="ml-auto hidden sm:block text-[10px] font-mono px-1.5 py-0.5 rounded border shrink-0"
                  style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
                >
                  ↵
                </kbd>
              )}
            </button>
          ))}
        </div>

        <div
          className="px-4 py-2 border-t flex items-center gap-3 text-[10px]"
          style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
        >
          <span>↑↓ navigate</span>
          <span>↵ open</span>
          <span className="ml-auto">Selecting a repository switches context</span>
        </div>
      </div>
    </div>
  );
}
