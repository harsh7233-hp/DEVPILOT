"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Branch } from "@/lib/api";
import { classNames } from "@/lib/utils";

interface BranchSelectorProps {
  owner: string;
  repo: string;
  value: string;
  onChange: (branch: string) => void;
  className?: string;
}

export function BranchSelector({ owner, repo, value, onChange, className = "" }: BranchSelectorProps) {
  const [open, setOpen] = useState(false);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const repoKey = owner && repo ? `${owner}/${repo}` : "";
  const [loadedKey, setLoadedKey] = useState("");

  // Reset cached branches when the repository changes (render-time adjustment).
  const [prevRepoKey, setPrevRepoKey] = useState(repoKey);
  if (prevRepoKey !== repoKey) {
    setPrevRepoKey(repoKey);
    setBranches([]);
    setError(null);
    setLoading(false);
    setLoadedKey("");
  }

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const loadBranches = useCallback(async () => {
    if (!owner || !repo || loadedKey === repoKey) return;
    setLoadedKey(repoKey);
    setLoading(true);
    setError(null);
    try {
      const res = await api.repositories.getBranches(owner, repo);
      setBranches(res.branches || []);
      if (!res.branches?.some((b) => b.name === value) && res.branches?.length > 0 && !value) {
        const def = res.branches.find((b) => b.is_default) || res.branches[0];
        onChange(def.name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load branches");
    } finally {
      setLoading(false);
    }
  }, [owner, repo, repoKey, loadedKey, value, onChange]);

  useEffect(() => {
    if (!open) return;
    queueMicrotask(() => void loadBranches());
  }, [open, loadBranches]);

  const sorted = [...branches].sort((a, b) => {
    if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div ref={containerRef} className={classNames("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        disabled={!owner || !repo}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={value ? `Branch: ${value}` : "Select branch"}
        className="w-full h-8 px-2.5 text-xs rounded-lg border flex items-center justify-between gap-1.5 transition-colors hover:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{
          borderColor: "var(--input-border)",
          background: "var(--btn-secondary-bg)",
          color: "var(--btn-secondary-text)",
        }}
      >
        <svg className="h-3.5 w-3.5 shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
        </svg>
        <span className="truncate max-w-[90px] sm:max-w-[130px]">{value || "branch"}</span>
        <svg className={classNames("h-3 w-3 shrink-0 transition-transform", open && "rotate-180")} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute right-0 z-50 mt-1 w-56 max-w-[calc(100vw-1.5rem)] rounded-lg border shadow-xl overflow-hidden"
          style={{ borderColor: "var(--border)", background: "var(--dropdown-bg)" }}
        >
          <div className="max-h-64 overflow-y-auto overscroll-contain py-1">
            {loading && (
              <div className="px-3 py-3 text-center text-xs" style={{ color: "var(--muted-foreground)" }}>
                Loading branches...
              </div>
            )}
            {error && !loading && (
              <div className="px-3 py-3 text-center text-xs text-red-500">{error}</div>
            )}
            {!loading && !error && sorted.length === 0 && (
              <div className="px-3 py-3 text-center text-xs" style={{ color: "var(--muted-foreground)" }}>
                No branches available
              </div>
            )}
            {!loading &&
              sorted.map((b) => (
                <button
                  key={b.name}
                  type="button"
                  role="option"
                  aria-selected={value === b.name}
                  onClick={() => {
                    onChange(b.name);
                    setOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left text-xs flex items-center gap-2 transition-colors min-h-[36px]"
                  style={{ color: "var(--foreground)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--dropdown-item-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <span className="truncate flex-1 font-mono">{b.name}</span>
                  {b.is_default && (
                    <span
                      className="text-[9px] uppercase tracking-wide px-1 py-0.5 rounded shrink-0"
                      style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
                    >
                      default
                    </span>
                  )}
                  {value === b.name && (
                    <svg className="h-3.5 w-3.5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  )}
                </button>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
