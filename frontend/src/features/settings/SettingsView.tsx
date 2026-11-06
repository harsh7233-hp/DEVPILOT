"use client";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useTheme } from "@/lib/theme-context";
import { useAuth } from "@/lib/auth-context";
import { useNotifications } from "@/lib/notification-context";
import { api } from "@/lib/api";

const NOTIFICATION_CATEGORIES = [
  { key: "security" as const, label: "Security", description: "Security findings and scan results" },
  { key: "performance" as const, label: "Performance", description: "Performance pattern detections" },
  { key: "repository" as const, label: "Repository", description: "New commits and repository activity" },
  { key: "pipeline" as const, label: "Pipeline", description: "CI/CD pipeline events" },
  { key: "dependency" as const, label: "Dependency", description: "Dependency vulnerability alerts" },
  { key: "analysis" as const, label: "Analysis", description: "Analysis completion events" },
  { key: "system" as const, label: "System", description: "System status and error notifications" },
] as const;

export function SettingsView() {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const { preferences, setPreferences, unread, refresh } = useNotifications();

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>Configure your DevPilot experience</p>
      </div>

      <Card>
        <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>Appearance</h2>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <p className="text-sm" style={{ color: "var(--foreground)" }}>Theme</p>
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>Select your preferred color scheme</p>
          </div>
          <div className="flex gap-2">
            <Button variant={theme === "light" ? "primary" : "secondary"} size="sm" onClick={() => setTheme("light")}>Light</Button>
            <Button variant={theme === "dark" ? "primary" : "secondary"} size="sm" onClick={() => setTheme("dark")}>Dark</Button>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>Notifications</h2>
        <p className="text-xs mb-4" style={{ color: "var(--muted-foreground)" }}>
          Choose which notification categories to receive. Notifications are created only from real repository events.
          {unread > 0 && <span className="ml-1 font-medium text-emerald-600 dark:text-emerald-400">{unread} unread notification(s).</span>}
        </p>
        <div className="space-y-3">
          {NOTIFICATION_CATEGORIES.map(({ key, label, description }) => (
            <label key={key} className="flex items-center justify-between gap-3 py-1 cursor-pointer">
              <div className="min-w-0">
                <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{label}</p>
                <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>{description}</p>
              </div>
              <button
                role="switch"
                aria-checked={preferences[key]}
                onClick={() => setPreferences({ [key]: !preferences[key] })}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${preferences[key] ? "bg-emerald-600" : "bg-zinc-300 dark:bg-zinc-600"}`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition-transform ${preferences[key] ? "translate-x-4" : "translate-x-0"}`}
                />
              </button>
            </label>
          ))}
        </div>
        <div className="mt-4 pt-3 border-t flex items-center gap-2" style={{ borderColor: "var(--border)" }}>
          <Button variant="secondary" size="sm" onClick={() => refresh()}>Refresh Notifications</Button>
          <Button variant="secondary" size="sm" onClick={() => api.notifications.markAllRead().then(() => refresh())}>Mark All Read</Button>
        </div>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>GitHub</h2>
        {user ? (
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3">
              {user.avatar_url && <img src={user.avatar_url} alt="" className="h-10 w-10 rounded-full" />}
              <div>
                <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{user.name || user.login}</p>
                <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>@{user.login}</p>
              </div>
            </div>
            <Button variant="danger" size="sm" onClick={() => logout()}>Disconnect</Button>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>No GitHub account connected</p>
            <a href={api.auth.getGithubUrl()}><Button size="sm">Connect GitHub</Button></a>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>About</h2>
        <div className="space-y-2 text-xs" style={{ color: "var(--muted-foreground)" }}>
          <p>DevPilot — AI-Powered Developer Platform</p>
          <p>Understand your codebase, visualize architecture, and predict the impact of every change.</p>
        </div>
      </Card>
    </div>
  );
}
