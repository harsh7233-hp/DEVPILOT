"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, type Notification } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface NotificationPreferences {
  security: boolean;
  performance: boolean;
  repository: boolean;
  pipeline: boolean;
  dependency: boolean;
  analysis: boolean;
  system: boolean;
}

interface NotificationContextType {
  notifications: Notification[];
  unread: number;
  loading: boolean;
  preferences: NotificationPreferences;
  loadMore: () => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  deleteNotification: (id: string) => void;
  refresh: () => void;
  setPreferences: (prefs: Partial<NotificationPreferences>) => void;
  hasMore: boolean;
}

const DEFAULT_PREFS: NotificationPreferences = {
  security: true,
  performance: true,
  repository: true,
  pipeline: true,
  dependency: true,
  analysis: true,
  system: true,
};

function loadPrefs(): NotificationPreferences {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const stored = localStorage.getItem("devpilot-notification-prefs");
    if (stored) return { ...DEFAULT_PREFS, ...JSON.parse(stored) };
  } catch { /* ignore */ }
  return DEFAULT_PREFS;
}

function savePrefs(prefs: NotificationPreferences) {
  if (typeof window === "undefined") return;
  try { localStorage.setItem("devpilot-notification-prefs", JSON.stringify(prefs)); } catch { /* ignore */ }
}

const NotificationContext = createContext<NotificationContextType | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [preferences, setPreferencesState] = useState<NotificationPreferences>(loadPrefs);
  const offsetRef = useRef(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchNotifications = useCallback(async (reset = false) => {
    try {
      setLoading(true);
      if (reset) offsetRef.current = 0;
      const limit = 20;
      const offset = reset ? 0 : offsetRef.current;
      const data = await api.notifications.list({ limit, offset });
      if (reset) {
        setNotifications(data.notifications);
      } else {
        setNotifications((prev) => [...prev, ...data.notifications]);
      }
      setUnread(data.unread);
      setHasMore(offset + data.notifications.length < data.total);
      offsetRef.current = offset + data.notifications.length;
    } catch {
      // silent — notifications are non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCount = useCallback(async () => {
    try {
      const data = await api.notifications.count();
      setUnread(data.unread);
    } catch { /* silent */ }
  }, []);

  const markRead = useCallback(async (id: string) => {
    try {
      const data = await api.notifications.markRead(id);
      setUnread(data.unread);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch { /* silent */ }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      const data = await api.notifications.markAllRead();
      setUnread(data.unread);
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch { /* silent */ }
  }, []);

  const deleteNotification = useCallback(async (id: string) => {
    try {
      const data = await api.notifications.delete(id);
      setUnread(data.unread);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch { /* silent */ }
  }, []);

  const loadMore = useCallback(() => {
    if (!loading && hasMore) fetchNotifications(false);
  }, [loading, hasMore, fetchNotifications]);

  const refresh = useCallback(() => fetchNotifications(true), [fetchNotifications]);

  const setPreferences = useCallback((prefs: Partial<NotificationPreferences>) => {
    setPreferencesState((prev) => {
      const next = { ...prev, ...prefs };
      savePrefs(next);
      return next;
    });
  }, []);

  // Poll for new notifications every 30 seconds (only when authenticated)
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      // Not authenticated — clear state and stop polling
      setNotifications([]);
      setUnread(0);
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    fetchNotifications(true);
    pollRef.current = setInterval(fetchCount, 30000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [authLoading, user, fetchNotifications, fetchCount]);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unread,
        loading,
        preferences,
        loadMore,
        markRead,
        markAllRead,
        deleteNotification,
        refresh,
        setPreferences,
        hasMore,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error("useNotifications must be used within NotificationProvider");
  return ctx;
}
