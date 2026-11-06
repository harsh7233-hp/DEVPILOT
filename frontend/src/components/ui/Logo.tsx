import Image from "next/image";
import Link from "next/link";
import { classNames } from "@/lib/utils";

export function LogoMark({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <Image
      src="/devpilot-logo.svg"
      alt=""
      width={size}
      height={size}
      priority
      unoptimized
      draggable={false}
      className={classNames(
        "rounded-lg shadow-sm ring-1 ring-black/10 dark:ring-white/15 select-none transition-[filter] duration-150 group-hover:brightness-110",
        className
      )}
    />
  );
}

/**
 * DevPilot brand lockup — the single clickable branding area.
 * Logo mark AND name navigate to /about.
 */
export function Logo({
  markSize = 28,
  className,
  nameClassName,
}: {
  markSize?: number;
  className?: string;
  nameClassName?: string;
}) {
  return (
    <Link
      href="/about"
      aria-label="About DevPilot"
      title="About DevPilot"
      className={classNames(
        "group flex items-center gap-2.5 min-w-0 rounded-lg px-1 py-1 -mx-1 transition-colors duration-150 hover:bg-[var(--muted)] active:scale-[0.98]",
        className
      )}
    >
      <LogoMark size={markSize} />
      <span
        className={classNames(
          "text-sm font-semibold tracking-tight truncate text-emerald-700 dark:text-emerald-300",
          nameClassName
        )}
      >
        DevPilot
      </span>
    </Link>
  );
}
