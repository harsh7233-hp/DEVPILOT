"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LogoMark as LogoMarkImage } from "@/components/ui/Logo";

/* ── Icons (inline SVG, stroke-based) ── */

function IconGitHub({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.55 0-.27-.01-1.17-.02-2.12-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.75 2.69 1.25 3.34.95.1-.74.4-1.25.72-1.53-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 015.8 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.42-2.7 5.39-5.27 5.68.41.35.78 1.05.78 2.12 0 1.53-.01 2.76-.01 3.14 0 .3.2.67.8.55A11.51 11.51 0 0023.5 12C23.5 5.65 18.35.5 12 .5z" />
    </svg>
  );
}

function IconSparkles({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
    </svg>
  );
}

function IconCode({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
    </svg>
  );
}

function IconLayers({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L12 12.75 6.429 9.75m11.142 0l4.179 2.25-9.75 5.25-9.75-5.25 4.179-2.25" />
    </svg>
  );
}

function IconChart({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  );
}

function IconFolder({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
    </svg>
  );
}

function IconBox({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
    </svg>
  );
}

function IconSearch({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
    </svg>
  );
}

function IconZap({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  );
}

function IconShield({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

/* ── Data ── */

const PIPELINE = [
  { title: "GitHub Repository", desc: "Connect any repo", icon: <IconGitHub /> },
  { title: "DevPilot AI", desc: "Intelligent engine", icon: <IconSparkles /> },
  { title: "Code Analysis", desc: "Deep AST parsing", icon: <IconCode /> },
  { title: "Architecture Graph", desc: "Live dependencies", icon: <IconLayers /> },
  { title: "Developer Insights", desc: "Actionable answers", icon: <IconChart /> },
];

const FEATURES = [
  {
    icon: <IconSparkles className="h-5 w-5" />,
    accent: "#10b981",
    title: "AI-Powered Code Analysis",
    desc: "Tree-sitter parsing extracts every function, class, and relationship from your codebase.",
  },
  {
    icon: <IconGitHub className="h-5 w-5" />,
    accent: "#6366f1",
    title: "GitHub Integration",
    desc: "Secure OAuth connection to your repositories. Analyze any branch in seconds.",
  },
  {
    icon: <IconFolder className="h-5 w-5" />,
    accent: "#f59e0b",
    title: "Repository Analysis",
    desc: "Full codebase scans with file filtering, language detection, and progress tracking.",
  },
  {
    icon: <IconLayers className="h-5 w-5" />,
    accent: "#8b5cf6",
    title: "Architecture Graph",
    desc: "Interactive dependency visualization. See how every module connects.",
  },
  {
    icon: <IconBox className="h-5 w-5" />,
    accent: "#ec4899",
    title: "Functions & Classes Explorer",
    desc: "Browse entities with locations, signatures, and cross-references.",
  },
  {
    icon: <IconSearch className="h-5 w-5" />,
    accent: "#06b6d4",
    title: "Codebase Insights",
    desc: "Ask questions in plain language. Get answers grounded in your actual code.",
  },
  {
    icon: <IconZap className="h-5 w-5" />,
    accent: "#ef4444",
    title: "Change Impact Engine",
    desc: "Predict what breaks before you ship, with graph-traversal risk scoring.",
  },
  {
    icon: <IconShield className="h-5 w-5" />,
    accent: "#84cc16",
    title: "Developer Productivity Tools",
    desc: "AI code review, semantic search, and impact analysis in one workspace.",
  },
];

/* ── Page ── */

export default function OverviewPage() {
  const router = useRouter();

  const handleStart = () => {
    router.push("/dashboard");
  };

  return (
    <div
      className="min-h-dvh flex flex-col"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      {/* Ambient background glow */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div
          className="absolute -top-32 left-1/2 -translate-x-1/2 h-[420px] w-[min(90vw,720px)] rounded-full opacity-[0.07] blur-3xl"
          style={{ background: "radial-gradient(closest-side, #10b981, transparent)" }}
        />
        <div
          className="absolute top-1/3 -right-40 h-[380px] w-[380px] rounded-full opacity-[0.05] blur-3xl"
          style={{ background: "radial-gradient(closest-side, #6366f1, transparent)" }}
        />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between gap-3 px-4 sm:px-6 h-14 shrink-0 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2.5 min-w-0">
          <Link href="/about" aria-label="About DevPilot" title="About DevPilot" className="flex items-center gap-2.5 min-w-0 rounded-lg px-0.5 py-0.5 -mx-0.5 transition-colors duration-150 hover:bg-[var(--muted)]">
            <LogoMark />
            <span className="text-sm font-semibold tracking-tight truncate">DevPilot</span>
          </Link>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />
          <button
            onClick={handleStart}
            className="hidden sm:inline-flex items-center justify-center h-9 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
            style={{ ["--tw-ring-offset-color" as string]: "var(--background)" }}
          >
            Go to Dashboard
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="relative z-10 flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 lg:py-16">
        {/* Hero */}
        <section className="text-center dp-fade-up">
          <div
            className="inline-flex items-center gap-2 h-8 px-3.5 rounded-full text-xs font-medium mb-6 border"
            style={{ background: "var(--card)", color: "var(--muted-foreground)", borderColor: "var(--border)" }}
          >
            <span className="relative flex h-2 w-2">
              <span className="dp-pulse absolute inline-flex h-full w-full rounded-full bg-emerald-500" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            AI-Powered Developer Platform
          </div>

          <h1 className="text-[2.5rem] leading-[1.05] sm:text-5xl sm:leading-[1.05] lg:text-6xl lg:leading-[1.05] font-bold tracking-tight">
            Dev<span className="bg-gradient-to-r from-emerald-500 via-teal-500 to-blue-500 bg-clip-text text-transparent">Pilot</span>
          </h1>

          <p className="mt-4 text-base sm:text-lg font-medium" style={{ color: "var(--foreground)" }}>
            Understand your code. Explore your architecture.{" "}
            <span className="bg-gradient-to-r from-emerald-600 to-blue-600 dark:from-emerald-400 dark:to-blue-400 bg-clip-text text-transparent font-semibold">
              Build smarter.
            </span>
          </p>

          <p className="mt-3 text-sm sm:text-base leading-relaxed max-w-xl mx-auto" style={{ color: "var(--muted-foreground)" }}>
            DevPilot analyzes your repositories, maps your architecture, explores every function
            and class, and delivers AI-powered insights grounded in your real code — not guesses.
          </p>
        </section>

        {/* Pipeline visual */}
        <section
          className="mt-12 sm:mt-16 dp-fade-up"
          style={{ animationDelay: "120ms" }}
          aria-label="How DevPilot works"
        >
          <p
            className="text-[11px] uppercase tracking-[0.18em] font-semibold text-center mb-6"
            style={{ color: "var(--muted-foreground)" }}
          >
            How it works
          </p>

          <ol className="flex flex-col md:flex-row items-stretch md:items-center justify-center list-none p-0 m-0">
            {PIPELINE.map((stage, i) => (
              <li key={stage.title} className="contents">
                <PipelineNode stage={stage} index={i} />
                {i < PIPELINE.length - 1 && <PipelineConnector delay={200 + i * 120} />}
              </li>
            ))}
          </ol>
        </section>

        {/* Features */}
        <section className="mt-14 sm:mt-20" aria-label="Features">
          <p
            className="text-[11px] uppercase tracking-[0.18em] font-semibold text-center mb-6"
            style={{ color: "var(--muted-foreground)" }}
          >
            Everything you need
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            {FEATURES.map((f, i) => (
              <article
                key={f.title}
                className="dp-fade-up group rounded-xl p-4 sm:p-5 border transition-colors duration-200 hover:border-[var(--border-hover)]"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  animationDelay: `${260 + i * 70}ms`,
                }}
              >
                <div
                  className="h-9 w-9 rounded-lg flex items-center justify-center mb-3 shrink-0"
                  style={{ background: `color-mix(in srgb, ${f.accent} 14%, transparent)`, color: f.accent }}
                >
                  {f.icon}
                </div>
                <h3 className="text-sm font-semibold leading-snug">{f.title}</h3>
                <p className="mt-1.5 text-xs leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
                  {f.desc}
                </p>
              </article>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="mt-14 sm:mt-20 pb-6 text-center dp-fade-up" style={{ animationDelay: "480ms" }}>
          <button
            onClick={handleStart}
            className="group inline-flex items-center justify-center gap-2.5 w-full sm:w-auto min-h-[52px] px-10 sm:px-12 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white text-base sm:text-lg font-semibold shadow-lg shadow-emerald-600/25 hover:shadow-emerald-500/30 transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
            style={{ ["--tw-ring-offset-color" as string]: "var(--background)" }}
          >
            Go to Dashboard
            <svg
              className="h-5 w-5 transition-transform duration-200 group-hover:translate-x-1"
              fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12l-7.5 7.5M21 12H3" />
            </svg>
          </button>
          <p className="mt-4 text-xs sm:text-sm px-2" style={{ color: "var(--muted-foreground)" }}>
            Connect your GitHub account and analyze your first repository in minutes.
          </p>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t py-4 px-4 text-center text-xs" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
        DevPilot — Built for developers who ship with confidence
      </footer>
    </div>
  );
}

/* ── Sub-components ── */

function LogoMark() {
  return <LogoMarkImage size={28} />;
}

function PipelineNode({
  stage,
  index,
}: {
  stage: (typeof PIPELINE)[number];
  index: number;
}) {
  const isAI = index === 1;
  return (
    <div
      className={`dp-fade-up relative flex items-center gap-3 md:flex-col md:text-center md:gap-2 rounded-xl px-3.5 py-3 md:px-4 md:py-4 border min-w-0 flex-1 ${
        isAI ? "md:-mt-1" : ""
      }`}
      style={{
        background: isAI
          ? "color-mix(in srgb, #10b981 8%, var(--card))"
          : "var(--card)",
        borderColor: isAI ? "color-mix(in srgb, #10b981 35%, var(--border))" : "var(--border)",
        animationDelay: `${140 + index * 110}ms`,
      }}
    >
      <div
        className={`h-9 w-9 md:h-10 md:w-10 rounded-lg flex items-center justify-center shrink-0 ${
          isAI ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" : ""
        }`}
        style={
          isAI
            ? undefined
            : { background: "var(--muted)", color: "var(--foreground)" }
        }
      >
        {stage.icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs sm:text-sm font-semibold leading-tight truncate md:whitespace-normal">
          {stage.title}
        </p>
        <p className="text-[10px] sm:text-xs mt-0.5 truncate md:whitespace-normal" style={{ color: "var(--muted-foreground)" }}>
          {stage.desc}
        </p>
      </div>
    </div>
  );
}

function PipelineConnector({ delay }: { delay: number }) {
  return (
    <div
      className="dp-fade-up flex items-center justify-center shrink-0 w-10 md:w-12 h-8 md:h-auto self-center"
      style={{ animationDelay: `${delay}ms` }}
      aria-hidden
    >
      {/* Mobile: vertical line + chevron */}
      <div className="flex flex-col items-center md:hidden">
        <div className="dp-flow-line w-px h-5 rounded-full" style={{ backgroundSize: "100% 200%" }} />
        <ChevronDown />
      </div>
      {/* Desktop: horizontal line + chevron */}
      <div className="hidden md:flex items-center">
        <div className="dp-flow-line h-px w-7 rounded-full" />
        <ChevronRight />
      </div>
    </div>
  );
}

function ChevronDown() {
  return (
    <svg className="h-3.5 w-3.5" style={{ color: "var(--muted-foreground)" }} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg className="h-3.5 w-3.5 -ml-1" style={{ color: "var(--muted-foreground)" }} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
    </svg>
  );
}
