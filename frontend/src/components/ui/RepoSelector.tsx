"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type GitHubRepo } from "@/lib/api";

interface RepoSelectorProps {
  value: string;
  onChange: (owner: string, repo: string) => void;
  className?: string;
  placeholder?: string;
}

export function RepoSelector({ value, onChange, className = "", placeholder = "Select Repository" }: RepoSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchRepos = useCallback(async () => {
    if (repos.length > 0) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.repositories.list();
      setRepos(res.repositories || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load repositories");
    } finally {
      setLoading(false);
    }
  }, [repos.length]);

  useEffect(() => {
    if (!open) return;
    setTimeout(() => inputRef.current?.focus(), 50);
    queueMicrotask(() => void fetchRepos());
  }, [open, fetchRepos]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return repos;
    const q = search.toLowerCase();
    return repos.filter(
      (r) =>
        r.full_name.toLowerCase().includes(q) ||
        r.name.toLowerCase().includes(q) ||
        r.owner.login.toLowerCase().includes(q)
    );
  }, [repos, search]);

  const handleSelect = useCallback(
    (repo: GitHubRepo) => {
      onChange(repo.owner.login, repo.name);
      setOpen(false);
      setSearch("");
    },
    [onChange]
  );

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="w-full h-10 px-3 text-sm rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-left flex items-center justify-between gap-2 transition-colors hover:border-zinc-300 dark:hover:border-zinc-600 active:scale-[0.99]"
      >
        <span className={value ? "text-zinc-900 dark:text-zinc-200 truncate" : "text-zinc-400 dark:text-zinc-500"}>
          {value || placeholder}
        </span>
        <svg className={`h-4 w-4 text-zinc-400 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute z-50 mt-1 w-full min-w-[240px] max-w-[calc(100vw-1.5rem)] rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-xl"
        >
          <div className="p-2 border-b border-zinc-100 dark:border-zinc-800">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search repositories..."
              className="w-full h-9 px-3 text-sm rounded-md bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-300 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:border-zinc-400 dark:focus:border-zinc-500"
            />
          </div>

          <div className="max-h-64 overflow-y-auto overscroll-contain">
            {loading && (
              <div className="p-4 text-center text-sm text-zinc-500">Loading repositories...</div>
            )}
            {error && (
              <div className="p-4 text-center text-sm text-red-500">{error}</div>
            )}
            {!loading && !error && filtered.length === 0 && (
              <div className="p-4 text-center text-sm text-zinc-500">
                {repos.length === 0 ? "No repositories found" : "No matches"}
              </div>
            )}
            {!loading && !error &&
              filtered.map((repo) => (
                <button
                  key={repo.id}
                  type="button"
                  onClick={() => handleSelect(repo)}
                  className={`w-full min-h-[44px] px-3 py-2.5 text-left text-sm flex items-center gap-2.5 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800 ${
                    value === repo.full_name ? "bg-emerald-50 dark:bg-emerald-500/10" : ""
                  }`}
                >
                  <div className="h-5 w-5 rounded bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center shrink-0">
                    <svg className="h-3 w-3 text-zinc-500 dark:text-zinc-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-zinc-900 dark:text-zinc-200 truncate">
                      {repo.owner.login}/{repo.name}
                    </p>
                    {repo.description && (
                      <p className="text-xs text-zinc-500 truncate mt-0.5">{repo.description}</p>
                    )}
                  </div>
                  {value === repo.full_name && (
                    <svg className="h-4 w-4 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
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
