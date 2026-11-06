"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

function useCloseDrawerOnNavigate() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pathname = usePathname();
  const [prevPath, setPrevPath] = useState(pathname);
  // Close drawer on navigation (render-time state adjustment)
  if (prevPath !== pathname) {
    setPrevPath(pathname);
    setDrawerOpen(false);
  }
  return { drawerOpen, setDrawerOpen };
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { drawerOpen, setDrawerOpen } = useCloseDrawerOnNavigate();

  return (
    <div className="flex h-dvh overflow-hidden" style={{ background: "var(--background)", color: "var(--foreground)" }}>
      <Sidebar mobileOpen={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TopNav onMenuClick={() => setDrawerOpen(true)} />
        <main className="flex-1 overflow-y-auto overscroll-contain">
          {children}
        </main>
      </div>
    </div>
  );
}
