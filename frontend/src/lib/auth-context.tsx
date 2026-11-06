"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { api, type GitHubUser } from "@/lib/api";

interface AuthState {
  user: GitHubUser | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<GitHubUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.auth.getMe();
      if (mountedRef.current) setUser(data.user);
    } catch (err) {
      if (mountedRef.current) setUser(null);
      if (mountedRef.current && err instanceof Error && !err.message.includes("401")) {
        setError(err.message);
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } finally {
      setUser(null);
      // Dispatch storage event for cross-tab repo state cleanup
      try {
        localStorage.removeItem("devpilot-selected-repo");
        window.dispatchEvent(new StorageEvent("storage", { key: "devpilot-selected-repo", newValue: null }));
      } catch { /* ignore */ }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const load = async () => {
      try {
        const data = await api.auth.getMe();
        if (mountedRef.current) setUser(data.user);
      } catch (err) {
        if (mountedRef.current) setUser(null);
        if (mountedRef.current && err instanceof Error && !err.message.includes("401")) {
          setError(err.message);
        }
      } finally {
        if (mountedRef.current) setLoading(false);
      }
    };
    void load();
    return () => { mountedRef.current = false; };
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, loading, error, refresh, logout }),
    [user, loading, error, refresh, logout]
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
