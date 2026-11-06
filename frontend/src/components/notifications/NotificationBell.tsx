"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useNotifications } from "@/lib/notification-context";
import type { Notification } from "@/lib/api";

const CATEGORY_ICONS: Record<string, string> = {
  security: "shield",
  performance: "zap",
  repository: "git-branch",
  pipeline: "pipeline",
  dependency: "package",
  analysis: "sparkles",
  system: "alert-circle",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#6b7280",
  info: "#3b82f6",
};

export function NotificationBell() {
  const { unread, notifications, markRead, markAllRead, deleteNotification, loading, loadMore, hasMore } = useNotifications();
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    if (open) document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  const handleNotificationClick = (n: Notification) => {
    if (!n.read) markRead(n.id);
    if (n.href) {
      setOpen(false);
      router.push(n.href);
    }
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen(!open)}
        aria-label={`Notifications${unread > 0 ? ` (${unread} unread)` : ""}`}
        className="relative h-9 w-9 sm:w-auto sm:px-2.5 flex items-center justify-center rounded-lg border transition-colors hover:brightness-95"
        style={{ borderColor: "var(--input-border)", color: "var(--muted-foreground)", background: "var(--btn-secondary-bg)" }}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unread > 0 && (
          <span
            className="absolute -top-1 -right-1 h-4 min-w-[16px] flex items-center justify-center text-[9px] font-bold rounded-full px-1 text-white"
            style={{ background: "#dc2626" }}
          >
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-[92vw] sm:w-96 max-h-[70vh] flex flex-col rounded-xl border shadow-xl z-50"
          style={{ borderColor: "var(--border)", background: "var(--card)" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
            <h3 className="text-sm font-semibold">Notifications</h3>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <button onClick={markAllRead} className="text-[10px] font-medium text-emerald-600 hover:text-emerald-500 dark:text-emerald-400 transition-colors">
                  Mark all read
                </button>
              )}
              <button onClick={() => setOpen(false)} className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Notification list */}
          <div className="flex-1 overflow-y-auto overscroll-contain">
            {notifications.length === 0 && !loading ? (
              <div className="py-12 text-center">
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>No notifications</p>
              </div>
            ) : (
              <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                {notifications.map((n) => (
                  <NotificationRow key={n.id} notification={n} onClick={() => handleNotificationClick(n)} onDelete={() => deleteNotification(n.id)} />
                ))}
              </div>
            )}
            {hasMore && (
              <button
                onClick={loadMore}
                disabled={loading}
                className="w-full py-2.5 text-[11px] font-medium text-center hover:bg-black/[0.03] dark:hover:bg-white/[0.03] transition-colors"
                style={{ color: "var(--muted-foreground)" }}
              >
                {loading ? "Loading..." : "Load more"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationRow({
  notification,
  onClick,
  onDelete,
}: {
  notification: Notification;
  onClick: () => void;
  onDelete: () => void;
}) {
  const timeAgo = formatTimeAgo(notification.created_at);
  const sevColor = SEVERITY_COLORS[notification.severity] || SEVERITY_COLORS.info;
  const catIcon = CATEGORY_ICONS[notification.category] || "bell";

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-black/[0.03] dark:hover:bg-white/[0.03] ${!notification.read ? "bg-emerald-50/50 dark:bg-emerald-500/5" : ""}`}
    >
      {/* Severity indicator */}
      <div className="relative shrink-0 mt-0.5">
        <span
          className="h-8 w-8 rounded-lg flex items-center justify-center text-[10px] font-medium"
          style={{ background: `color-mix(in srgb, ${sevColor} 12%, transparent)`, color: sevColor }}
        >
          {catIcon}
        </span>
        {!notification.read && (
          <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full" style={{ background: "#10b981" }} />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className={`text-xs font-medium leading-tight ${!notification.read ? "" : "opacity-80"}`}>
          {notification.title}
        </p>
        <p className="text-[10px] mt-0.5 leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
          {notification.message}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[9px]" style={{ color: "var(--muted-foreground)" }}>{timeAgo}</span>
          {notification.repo && (
            <span className="text-[9px] font-mono" style={{ color: "var(--muted-foreground)" }}>{notification.owner}/{notification.repo}</span>
          )}
        </div>
      </div>

      {/* Delete */}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="shrink-0 h-6 w-6 flex items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-black/5 dark:hover:bg-white/5 transition-all"
        style={{ color: "var(--muted-foreground)" }}
        aria-label="Delete notification"
      >
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </button>
  );
}

function formatTimeAgo(timestamp: number): string {
  const now = Math.floor(Date.now() / 1000);
  const diff = now - timestamp;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(timestamp * 1000).toLocaleDateString();
}
