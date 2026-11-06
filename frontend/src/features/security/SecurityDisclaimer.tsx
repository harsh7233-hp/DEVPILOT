"use client";

import { useEffect, useId, useRef, useState } from "react";

export const SECURITY_DISCLAIMER =
  "Automated security analysis may not detect all vulnerabilities. Results are indicative and do not guarantee complete security.";

export const SECURITY_DISCLAIMER_DETAIL =
  "DevPilot uses automated analysis techniques to identify potential security vulnerabilities in your code. However, automated testing has limitations and may not identify every security issue, hidden vulnerability, or potential attack vector. Therefore, a clean security report does not mean your code is completely secure. We recommend manual code reviews, additional security testing, and professional audits before deploying applications to production.";

interface SecurityDisclaimerProps {
  className?: string;
  placement?: "top" | "bottom";
}

export function SecurityDisclaimer({ className = "", placement = "top" }: SecurityDisclaimerProps) {
  const [pinned, setPinned] = useState(false);
  const [hovered, setHovered] = useState(false);
  const infoRef = useRef<HTMLDivElement>(null);
  const detailId = useId();
  const open = pinned || hovered;

  useEffect(() => {
    if (!pinned) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (infoRef.current && !infoRef.current.contains(event.target as Node)) {
        setPinned(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPinned(false);
        setHovered(false);
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [pinned]);

  const handleToggle = () => {
    if (pinned) {
      setPinned(false);
      setHovered(false);
    } else {
      setPinned(true);
    }
  };

  return (
    <div
      className={`rounded-lg p-2.5 text-[10px] sm:text-[11px] leading-relaxed ${className}`}
      style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
    >
      <div className="flex items-start gap-1.5">
        <p className="flex-1" role="note">{SECURITY_DISCLAIMER}</p>
        <div
          ref={infoRef}
          className="relative shrink-0"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onFocus={() => setHovered(true)}
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node)) {
              setHovered(false);
            }
          }}
        >
          <button
            type="button"
            onClick={handleToggle}
            aria-label="More information about automated security analysis limitations"
            aria-expanded={open}
            aria-describedby={open ? detailId : undefined}
            className="inline-flex h-6 w-6 items-center justify-center rounded-full border transition-colors hover:bg-black/[0.04] dark:hover:bg-white/[0.06] focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60"
            style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10.5v6M12 7.5h.01" />
            </svg>
          </button>
          {open && (
            <div
              id={detailId}
              role="tooltip"
              className={`absolute right-0 z-20 w-72 max-w-[calc(100vw-2rem)] rounded-lg border p-3 text-[10px] sm:text-[11px] leading-relaxed shadow-lg ${
                placement === "top" ? "bottom-full mb-2" : "top-full mt-2"
              }`}
              style={{ background: "var(--dropdown-bg)", borderColor: "var(--border)", color: "var(--foreground)" }}
            >
              {SECURITY_DISCLAIMER_DETAIL}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
