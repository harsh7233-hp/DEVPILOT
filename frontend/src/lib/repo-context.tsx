"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { GitHubRepo } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export interface SelectedRepo {
  owner: string;
  name: string;
  fullName: string;
  defaultBranch: string;
  language?: string;
  description?: string;
}

interface RepoState {
  repo: SelectedRepo | null;
  branch: string;
  setRepo: (repo: GitHubRepo) => void;
  setBranch: (branch: string) => void;
  clear: () => void;
  hydrated: boolean;
}

const RepoContext = createContext<RepoState | null>(null);

const STORAGE_KEY = "devpilot-selected-repo";

function loadStored(): { repo: SelectedRepo | null; branch: string } {
  if (typeof window === "undefined") return { repo: null, branch: "" };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { repo: null, branch: "" };
    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed.owner === "string" &&
      typeof parsed.name === "string" &&
      parsed.owner &&
      parsed.name
    ) {
      return {
        repo: {
          owner: parsed.owner,
          name: parsed.name,
          fullName: parsed.fullName || `${parsed.owner}/${parsed.name}`,
          defaultBranch: parsed.defaultBranch || "main",
          language: parsed.language,
          description: parsed.description,
        },
        branch: parsed.branch || parsed.defaultBranch || "main",
      };
    }
  } catch {
    /* ignore */
  }
  return { repo: null, branch: "" };
}

export function RepoProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [repo, setRepoState] = useState<SelectedRepo | null>(null);
  const [branch, setBranchState] = useState("");
  const [hydrated, setHydrated] = useState(false);

  const persist = useCallback((r: SelectedRepo | null, b: string) => {
    try {
      if (!r) localStorage.removeItem(STORAGE_KEY);
      else
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ ...r, branch: b })
        );
    } catch {
      /* ignore */
    }
  }, []);

  const clear = useCallback(() => {
    setRepoState(null);
    setBranchState("");
    persist(null, "");
  }, [persist]);

  // Hydrate from localStorage on mount
  useEffect(() => {
    queueMicrotask(() => {
      const stored = loadStored();
      setRepoState(stored.repo);
      setBranchState(stored.branch);
      setHydrated(true);
    });
  }, []);

  // When auth finishes loading: if no user, clear repo (stale state).
  // If user exists but stored repo is from a different session, we keep it
  // (user may have reconnected to the same account).
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      // Not authenticated — clear any stale repo selection
      clear();
    }
  }, [authLoading, user, clear]);

  // Cross-tab: listen for storage removal (logout in another tab)
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue === null) {
        setRepoState(null);
        setBranchState("");
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const setRepo = useCallback(
    (ghRepo: GitHubRepo) => {
      const next: SelectedRepo = {
        owner: ghRepo.owner.login,
        name: ghRepo.name,
        fullName: ghRepo.full_name,
        defaultBranch: ghRepo.default_branch || "main",
        language: ghRepo.language,
        description: ghRepo.description,
      };
      const nextBranch = next.defaultBranch;
      setRepoState(next);
      setBranchState(nextBranch);
      persist(next, nextBranch);
    },
    [persist]
  );

  const setBranch = useCallback(
    (b: string) => {
      setBranchState(b);
      if (repo) persist(repo, b);
    },
    [repo, persist]
  );

  const value = useMemo<RepoState>(
    () => ({ repo, branch, setRepo, setBranch, clear, hydrated }),
    [repo, branch, setRepo, setBranch, clear, hydrated]
  );

  return <RepoContext.Provider value={value}>{children}</RepoContext.Provider>;
}

export function useSelectedRepo(): RepoState {
  const ctx = useContext(RepoContext);
  if (!ctx) throw new Error("useSelectedRepo must be used within RepoProvider");
  return ctx;
}
