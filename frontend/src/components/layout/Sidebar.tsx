"use client";

import Link from "next/link";
import Image from "next/image";
import { useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { classNames } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { useSelectedRepo } from "@/lib/repo-context";
import { Logo, LogoMark } from "@/components/ui/Logo";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

interface NavSection {
  label: string;
  collapsible?: boolean;
  items: NavItem[];
}

const sections: NavSection[] = [
  {
    label: "WORKSPACE",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: <IconDashboard /> },
      { label: "Command Center", href: "/command-center", icon: <IconTerminal /> },
    ],
  },
  {
    label: "ANALYZE",
    collapsible: true,
    items: [
      { label: "Code Intelligence", href: "/intelligence", icon: <IconIntelligence /> },
      { label: "Code Health", href: "/security", icon: <IconHealth /> },
      { label: "Impact Analysis", href: "/impact-analysis", icon: <IconImpact /> },
      { label: "Architecture", href: "/architecture", icon: <IconArchitecture /> },
    ],
  },
  {
    label: "DEVELOP",
    collapsible: true,
    items: [
      { label: "Code Explorer", href: "/code-explorer", icon: <IconCode /> },
      { label: "Code Review", href: "/code-review", icon: <IconReview /> },
      { label: "Pipelines", href: "/pipelines", icon: <IconPipelines /> },
    ],
  },
  {
    label: "AI",
    collapsible: true,
    items: [
      { label: "AI Assistant", href: "/ai-assistant", icon: <IconAI /> },
    ],
  },
  {
    label: "MANAGE",
    collapsible: true,
    items: [
      { label: "Repositories", href: "/repositories", icon: <IconRepos /> },
      { label: "Settings", href: "/settings", icon: <IconSettings /> },
    ],
  },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

function groupForPath(pathname: string): string | null {
  for (const section of sections) {
    if (!section.collapsible) continue;
    const match = section.items.some(
      (item) => pathname === item.href || pathname.startsWith(item.href + "/")
    );
    if (match) return section.label;
  }
  return null;
}

export function Sidebar({ mobileOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { repo } = useSelectedRepo();
  const [collapsed, setCollapsed] = useState(false);
  const routeGroup = groupForPath(pathname);
  const [tapGroup, setTapGroup] = useState<string | null>(null);
  const [hoverGroup, setHoverGroup] = useState<string | null>(null);
  const openTimer = useRef<number | null>(null);
  const closeTimer = useRef<number | null>(null);
  const [prevPath, setPrevPath] = useState(pathname);
  if (prevPath !== pathname) {
    setPrevPath(pathname);
    setTapGroup(null);
    setHoverGroup(null);
  }
  const openGroup = tapGroup ?? hoverGroup ?? routeGroup;

  function clearGroupTimers() {
    if (openTimer.current !== null) {
      window.clearTimeout(openTimer.current);
      openTimer.current = null;
    }
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }

  function handleEnter(label: string) {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
    if (openTimer.current !== null) window.clearTimeout(openTimer.current);
    openTimer.current = window.setTimeout(() => setHoverGroup(label), 120);
  }

  function handleLeave() {
    if (openTimer.current !== null) {
      window.clearTimeout(openTimer.current);
      openTimer.current = null;
    }
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setHoverGroup(null), 200);
  }

  function handleTap(label: string) {
    clearGroupTimers();
    setHoverGroup(null);
    setTapGroup((prev) => (prev === label ? null : label));
  }

  return (
    <>
      {/* Mobile overlay */}
      <div
        aria-hidden={!mobileOpen}
        onClick={onClose}
        className={classNames(
          "fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px] transition-opacity duration-200 lg:hidden",
          mobileOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
      />

      <aside
        className={classNames(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r transition-all duration-200 ease-out",
          "w-56 max-w-[80vw] lg:static lg:shrink-0",
          isCollapsed() ? "lg:w-[60px]" : "lg:w-52",
          mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full lg:translate-x-0"
        )}
        style={{ borderColor: "var(--sidebar-border)", background: "var(--sidebar-bg)" }}
        aria-label="Main navigation"
      >
        {/* Logo */}
        <div className={classNames("border-b shrink-0", isCollapsed() ? "px-2 py-2.5" : "px-3 py-2.5")} style={{ borderColor: "var(--sidebar-border)" }}>
          {isCollapsed() ? (
            <Link href="/about" className="flex items-center justify-center rounded-md transition-colors hover:bg-black/5 dark:hover:bg-white/5 p-1" onClick={onClose} title="About DevPilot">
              <LogoMark size={24} />
            </Link>
          ) : (
            <div className="flex items-center justify-between">
              <Logo markSize={26} nameClassName="text-sm" />
              <button
                onClick={() => setCollapsed(true)}
                aria-label="Collapse sidebar"
                className="hidden lg:flex h-6 w-6 items-center justify-center rounded transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                style={{ color: "var(--muted-foreground)" }}
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
              </button>
            </div>
          )}
          {/* Expand button when collapsed */}
          {isCollapsed() && (
            <button
              onClick={() => setCollapsed(false)}
              aria-label="Expand sidebar"
              className="hidden lg:flex mt-2 h-6 w-full items-center justify-center rounded transition-colors hover:bg-black/5 dark:hover:bg-white/5"
              style={{ color: "var(--muted-foreground)" }}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          )}
        </div>

        {/* Repository indicator */}
        {user && repo && !isCollapsed() && (
          <div className="px-3 py-2 border-b" style={{ borderColor: "var(--sidebar-border)" }}>
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-md" style={{ background: "var(--muted)" }}>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
              <span className="text-[11px] font-medium truncate" style={{ color: "var(--foreground)" }}>
                {repo.name}
              </span>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto overscroll-contain py-1.5">
          {sections.map((section) => {
            const groupOpen = openGroup === section.label;
            const forWorkspace = !section.collapsible;
            return (
              <div
                key={section.label}
                className="mb-3"
                onMouseEnter={section.collapsible ? () => handleEnter(section.label) : undefined}
                onMouseLeave={section.collapsible ? handleLeave : undefined}
              >
                {/* Collapsed sidebar: flat icon rows always */}
                {isCollapsed() && (
                  <div className="px-3 pt-2 pb-0.5"><div className="h-px" style={{ background: "var(--border)" }} /></div>
                )}
                {!isCollapsed() && (
                  <>
                    {/* Group header */}
                    <div className="px-3 pt-3 pb-1">
                      {forWorkspace ? (
                        <span className="text-sm uppercase tracking-widest font-semibold" style={{ color: "var(--muted-foreground)" }}>
                          {section.label}
                        </span>
                      ) : (
                        <div
                          className={classNames(
                            "flex items-center justify-between rounded-md pl-1.5 pr-1 h-7 transition-colors duration-150 hover:bg-black/5 dark:hover:bg-white/5",
                            groupOpen ? "text-[var(--foreground)]" : "text-[var(--muted-foreground)]"
                          )}
                          role="button"
                          tabIndex={0}
                          aria-expanded={groupOpen}
                          onClick={() => handleTap(section.label)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              handleTap(section.label);
                            }
                          }}
                        >
                          <span className="text-sm uppercase tracking-widest font-semibold">{section.label}</span>
                          <IconChevron
                            className="h-3.5 w-3.5 transition-transform duration-200"
                            rotated={groupOpen}
                          />
                        </div>
                      )}
                    </div>
                  </>
                )}

                {isCollapsed() ? (
                  <div className={classNames("space-y-0.5", "px-2")}>
                    {section.items.map((item) => (
                      <NavRow key={item.href} item={item} pathname={pathname} onClose={onClose} collapsed />
                    ))}
                  </div>
                ) : (
                  <div className="px-2">
                    {forWorkspace ? (
                      <div className="space-y-0.5">
                        {section.items.map((item) => (
                          <NavRow key={item.href} item={item} pathname={pathname} onClose={onClose} />
                        ))}
                      </div>
                    ) : (
                      <>
                        {/* Subsection drawer */}
                        <div
                          className={classNames(
                            "overflow-hidden transition-[max-height,opacity] duration-200 ease-out",
                            groupOpen ? "max-h-64 opacity-100" : "max-h-0 opacity-0"
                          )}
                          aria-hidden={!groupOpen}
                        >
                          <div className="mt-0.5 space-y-0.5 border-l ml-[10px] pl-2" style={{ borderColor: "var(--border)" }}>
                            {section.items.map((item) => {
                              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                              return (
                                <Link
                                  key={item.href}
                                  href={item.href}
                                  onClick={onClose}
                                  className={classNames(
                                    "flex items-center gap-2 rounded-md text-[13px] font-medium transition-colors duration-150",
                                    "h-8 px-2.5",
                                    isActive
                                      ? "bg-emerald-500/10 text-emerald-400"
                                      : "text-[var(--muted-foreground)] hover:bg-black/5 hover:text-[var(--foreground)] dark:hover:bg-white/5"
                                  )}
                                >
                                  <span className="shrink-0 [&>svg]:h-4 [&>svg]:w-4">{item.icon}</span>
                                  <span className="truncate">{item.label}</span>
                                </Link>
                              );
                            })}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* User section */}
        <div className="border-t shrink-0 px-2 py-2" style={{ borderColor: "var(--sidebar-border)" }}>
          {isCollapsed() ? (
            <div className="flex justify-center">
              {user?.avatar_url ? (
                <Image src={user.avatar_url} alt={user.login} width={26} height={26} className="rounded-full" unoptimized />
              ) : (
                <div className="h-6.5 w-6.5 rounded-full flex items-center justify-center text-[9px] font-medium" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
                  {user?.login?.slice(0, 2).toUpperCase() ?? "??"}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 px-2 py-1">
              {user?.avatar_url ? (
                <Image src={user.avatar_url} alt={user.login} width={24} height={24} className="rounded-full shrink-0" unoptimized />
              ) : (
                <div className="h-6 w-6 rounded-full flex items-center justify-center text-[9px] font-medium shrink-0" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
                  {user?.login?.slice(0, 2).toUpperCase() ?? "??"}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-medium truncate" style={{ color: "var(--foreground)" }}>{user?.name || user?.login || "Not connected"}</p>
                <p className="text-[9px] truncate" style={{ color: "var(--muted-foreground)" }}>{user ? `@${user.login}` : "Connect GitHub"}</p>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );

  function isCollapsed() {
    return collapsed;
  }
}

/* ── Icons ── */

function IconDashboard() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
    </svg>
  );
}

function IconTerminal() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" />
    </svg>
  );
}

function IconIntelligence() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
    </svg>
  );
}

function IconHealth() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

function IconImpact() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
    </svg>
  );
}

function IconArchitecture() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L12 12.75 6.429 9.75m11.142 0l4.179 2.25-9.75 5.25-9.75-5.25 4.179-2.25" />
    </svg>
  );
}

function IconCode() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
    </svg>
  );
}

function IconReview() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function IconPipelines() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 12v1.5m10.5-3.375V12M17.25 12a2.25 2.25 0 00-2.25 2.25v4.5c0 .621-.504 1.125-1.125 1.125h-3" />
    </svg>
  );
}

function IconAI() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
    </svg>
  );
}

function IconRepos() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  );
}

function IconSettings() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function IconChevron({ className, rotated }: { className?: string; rotated?: boolean }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.8}
      stroke="currentColor"
      aria-hidden
      style={{ transform: rotated ? "rotate(90deg)" : undefined }}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
    </svg>
  );
}

function NavRow({
  item,
  pathname,
  onClose,
  collapsed,
}: {
  item: NavItem;
  pathname: string;
  onClose?: () => void;
  collapsed?: boolean;
}) {
  const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
  return (
    <Link
      href={item.href}
      onClick={onClose}
      title={collapsed ? item.label : undefined}
      className={classNames(
        "flex items-center gap-2 rounded-md text-[13px] font-medium transition-all duration-150",
        collapsed ? "justify-center h-9 w-full" : "h-8 px-2.5",
        isActive
          ? "bg-emerald-500/10 text-emerald-400"
          : "hover:bg-black/5 dark:hover:bg-white/5"
      )}
      style={!isActive ? { color: "var(--muted-foreground)" } : undefined}
    >
      <span className="shrink-0 [&>svg]:h-4 [&>svg]:w-4">{item.icon}</span>
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}
