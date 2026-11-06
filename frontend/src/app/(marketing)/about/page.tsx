"use client";

import Link from "next/link";
import Image from "next/image";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { LogoMark } from "@/components/ui/Logo";

/* ── Icons ── */

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

function IconLayers({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.429 9.75L2.25 12l4.179 2.25m0-4.5l5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L12 12.75 6.429 9.75m11.142 0l4.179 2.25-9.75 5.25-9.75-5.25 4.179-2.25" />
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

function IconCode({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
    </svg>
  );
}

/* ── Data ── */

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Connect GitHub",
    desc: "Sign in securely with GitHub OAuth and pick any repository you own or collaborate on.",
  },
  {
    step: "02",
    title: "Analyze the Codebase",
    desc: "DevPilot clones and scans your repo with Tree-sitter parsers, extracting every function, class, API route, and import.",
  },
  {
    step: "03",
    title: "Build the Knowledge Graph",
    desc: "Entities and their relationships become a live dependency graph — your architecture, mapped automatically.",
  },
  {
    step: "04",
    title: "Ask, Explore, Review",
    desc: "Query your codebase in plain language, trace change impact, and get AI code reviews grounded in real code.",
  },
];

const FEATURES = [
  {
    icon: <IconGitHub className="h-5 w-5" />,
    accent: "#6366f1",
    title: "GitHub Repository Integration",
    desc: "Secure OAuth connection to your GitHub account. Browse repositories, trigger analyses, and track progress in real time.",
  },
  {
    icon: <IconCode className="h-5 w-5" />,
    accent: "#f59e0b",
    title: "AI-Powered Code Analysis",
    desc: "Tree-sitter AST parsing understands TypeScript, JavaScript, Python and more — down to individual functions and classes.",
  },
  {
    icon: <IconLayers className="h-5 w-5" />,
    accent: "#8b5cf6",
    title: "Architecture & Dependency Visualization",
    desc: "An interactive React Flow graph shows how every module, service, and component depends on each other.",
  },
  {
    icon: <IconBox className="h-5 w-5" />,
    accent: "#ec4899",
    title: "Functions & Classes Analysis",
    desc: "Explore every entity with its file location, line numbers, signature, incoming and outgoing references.",
  },
  {
    icon: <IconSearch className="h-5 w-5" />,
    accent: "#06b6d4",
    title: "Codebase Insights",
    desc: "Ask questions like \u201cwhere is auth handled?\u201d and get answers extracted from your actual source files, not guesses.",
  },
  {
    icon: <IconZap className="h-5 w-5" />,
    accent: "#ef4444",
    title: "Change Impact Engine",
    desc: "Select any function or file and see exactly what breaks downstream — with graph-traversal risk scoring before you ship.",
  },
  {
    icon: <IconShield className="h-5 w-5" />,
    accent: "#84cc16",
    title: "AI Code Review",
    desc: "Paste code or diffs and receive severity-ranked feedback combining static analysis and AI reasoning.",
  },
  {
    icon: <IconSparkles className="h-5 w-5" />,
    accent: "#10b981",
    title: "Developer Productivity Workspace",
    desc: "Dashboards, semantic search, impact reports, and an AI assistant — one cohesive tool instead of five tabs.",
  },
];

/* ── Page ── */

export default function AboutPage() {
  return (
    <div
      className="min-h-dvh flex flex-col"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      {/* Ambient glows */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div
          className="absolute -top-32 left-1/4 h-[420px] w-[min(90vw,640px)] rounded-full opacity-[0.07] blur-3xl"
          style={{ background: "radial-gradient(closest-side, #10b981, transparent)" }}
        />
        <div
          className="absolute top-1/2 -right-40 h-[380px] w-[380px] rounded-full opacity-[0.05] blur-3xl"
          style={{ background: "radial-gradient(closest-side, #8b5cf6, transparent)" }}
        />
      </div>

      {/* Header */}
      <header
        className="relative z-10 flex items-center justify-between gap-3 px-4 sm:px-6 h-14 shrink-0 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <LogoMark size={28} />
          <span className="text-sm font-semibold tracking-tight truncate text-emerald-700 dark:text-emerald-300">DevPilot</span>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />
          <Link
            href="/command-center"
            className="inline-flex items-center justify-center gap-1.5 h-9 px-3 sm:px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white text-sm font-semibold transition-colors whitespace-nowrap"
          >
            Back to Command Center
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12l-7.5 7.5M21 12H3" />
            </svg>
          </Link>
        </div>
      </header>

      {/* Main */}
      <main className="relative z-10 flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 lg:py-16">
        {/* Hero */}
        <section className="text-center max-w-3xl mx-auto dp-fade-up">
          <Image
            src="/devpilot-logo.svg"
            alt="The DevPilot logo"
            width={1024}
            height={1024}
            priority
            unoptimized
            className="mx-auto h-40 sm:h-48 w-auto mb-8 drop-shadow-lg"
          />
          <div
            className="inline-flex items-center gap-2 h-8 px-3.5 rounded-full text-xs font-medium mb-6 border"
            style={{ background: "var(--card)", color: "var(--muted-foreground)", borderColor: "var(--border)" }}
          >
            <span className="relative flex h-2 w-2">
              <span className="dp-pulse absolute inline-flex h-full w-full rounded-full bg-emerald-500" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            About DevPilot
          </div>

          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-[1.1]">
            Your codebase,{" "}
            <span className="bg-gradient-to-r from-emerald-500 via-teal-500 to-blue-500 bg-clip-text text-transparent">
              finally understood.
            </span>
          </h1>

          <p className="mt-5 text-sm sm:text-base leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
            DevPilot is an AI-powered developer platform that turns any GitHub repository into a
            living map of your software — analyzing code structure, visualizing architecture, and
            answering questions with grounded, code-level intelligence.
          </p>
        </section>

        {/* What / Problem */}
        <section
          className="mt-12 sm:mt-16 grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-5"
          aria-label="What DevPilot does"
        >
          <article
            className="dp-fade-up rounded-xl p-5 sm:p-6 border"
            style={{ background: "var(--card)", borderColor: "var(--border)", animationDelay: "100ms" }}
          >
            <div
              className="h-9 w-9 rounded-lg flex items-center justify-center mb-4"
              style={{ background: "color-mix(in srgb, #10b981 14%, transparent)", color: "#10b981" }}
            >
              <IconSparkles />
            </div>
            <h2 className="text-base sm:text-lg font-semibold">What is DevPilot?</h2>
            <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
              DevPilot connects to your GitHub account, deeply analyzes your repositories using
              Tree-sitter AST parsing, and builds a knowledge graph of every function, class, and
              relationship in your code. On top of that graph sits an AI layer — powered by Groq —
              that answers questions, reviews code, and predicts the impact of changes.
            </p>
          </article>

          <article
            className="dp-fade-up rounded-xl p-5 sm:p-6 border"
            style={{ background: "var(--card)", borderColor: "var(--border)", animationDelay: "180ms" }}
          >
            <div
              className="h-9 w-9 rounded-lg flex items-center justify-center mb-4"
              style={{ background: "color-mix(in srgb, #ef4444 14%, transparent)", color: "#ef4444" }}
            >
              <IconZap />
            </div>
            <h2 className="text-base sm:text-lg font-semibold">The problem it solves</h2>
            <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
              Developers lose hours navigating unfamiliar code, tracing dependencies by hand, and
              discovering breakage only after shipping. DevPilot eliminates the guesswork: see your
              architecture at a glance, know what a change will affect before you commit, and ask
              your codebase questions directly instead of grepping through folders.
            </p>
          </article>
        </section>

        {/* Visualization */}
        <section
          className="mt-12 sm:mt-16 dp-fade-up"
          style={{ animationDelay: "240ms" }}
          aria-label="Dependency visualization example"
        >
          <div
            className="rounded-xl border overflow-hidden"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div
              className="px-4 sm:px-5 py-3 border-b flex items-center gap-2"
              style={{ borderColor: "var(--border)" }}
            >
              <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
              <span className="ml-2 text-xs font-mono truncate" style={{ color: "var(--muted-foreground)" }}>
                architecture-explorer — live dependency graph
              </span>
            </div>
            <DependencyGraphMock />
          </div>
        </section>

        {/* How it works */}
        <section className="mt-14 sm:mt-20" aria-label="How DevPilot works">
          <SectionLabel>How DevPilot works</SectionLabel>
          <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 list-none p-0 m-0">
            {HOW_IT_WORKS.map((s, i) => (
              <li
                key={s.step}
                className="dp-fade-up relative rounded-xl p-4 sm:p-5 border"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  animationDelay: `${300 + i * 90}ms`,
                }}
              >
                <span
                  className="text-2xl font-bold tracking-tight"
                  style={{
                    color: "color-mix(in srgb, #10b981 70%, var(--foreground))",
                    opacity: 0.85,
                  }}
                >
                  {s.step}
                </span>
                <h3 className="mt-2 text-sm font-semibold">{s.title}</h3>
                <p className="mt-1.5 text-xs leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
                  {s.desc}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* Features */}
        <section className="mt-14 sm:mt-20" aria-label="Feature highlights">
          <SectionLabel>Everything built in</SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            {FEATURES.map((f, i) => (
              <article
                key={f.title}
                className="dp-fade-up group rounded-xl p-4 sm:p-5 border transition-colors duration-200 hover:border-[var(--border-hover)]"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  animationDelay: `${420 + i * 60}ms`,
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
        <section
          className="mt-14 sm:mt-20 mb-4 dp-fade-up rounded-2xl border p-6 sm:p-10 text-center"
          style={{
            background:
              "linear-gradient(135deg, color-mix(in srgb, #10b981 8%, var(--card)), var(--card))",
            borderColor: "color-mix(in srgb, #10b981 30%, var(--border))",
            animationDelay: "600ms",
          }}
        >
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight">
            Ready to explore your codebase?
          </h2>
          <p className="mt-2 text-sm max-w-md mx-auto" style={{ color: "var(--muted-foreground)" }}>
            Jump into the Command Center to connect a repository, map your architecture, and put DevPilot&apos;s AI to work.
          </p>
          <Link
            href="/command-center"
            className="group mt-6 inline-flex items-center justify-center gap-2.5 w-full sm:w-auto max-w-sm min-h-[52px] px-10 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white text-base font-semibold shadow-lg shadow-emerald-600/25 hover:shadow-emerald-500/30 transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
            style={{ ["--tw-ring-offset-color" as string]: "var(--background)" }}
          >
            Back to Command Center
            <svg
              className="h-5 w-5 transition-transform duration-200 group-hover:translate-x-1"
              fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12l-7.5 7.5M21 12H3" />
            </svg>
          </Link>
        </section>
      </main>

      {/* Footer */}
      <footer
        className="relative z-10 border-t py-4 px-4 text-center text-xs"
        style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
      >
        DevPilot — Built for developers who ship with confidence
      </footer>
    </div>
  );
}

/* ── Sub-components ── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="text-[11px] uppercase tracking-[0.18em] font-semibold text-center mb-6"
      style={{ color: "var(--muted-foreground)" }}
    >
      {children}
    </p>
  );
}

/** Theme-aware mini dependency-graph illustration. Scales via viewBox. */
function DependencyGraphMock() {
  const nodeFill = "var(--card)";
  const nodeStroke = "var(--border-hover)";
  const labelFill = "var(--foreground)";
  const subFill = "var(--muted-foreground)";

  const nodes = [
    { x: 300, y: 52, label: "app.ts", sub: "entry", accent: "#10b981" },
    { x: 120, y: 150, label: "router", sub: "module", accent: "#6366f1" },
    { x: 480, y: 150, label: "auth.ts", sub: "service", accent: "#f59e0b" },
    { x: 60, y: 252, label: "UserRepo", sub: "class", accent: "#ec4899" },
    { x: 210, y: 252, label: "getUser()", sub: "function", accent: "#8b5cf6" },
    { x: 390, y: 252, label: "/api/auth", sub: "route", accent: "#06b6d4" },
    { x: 540, y: 252, label: "jwt.ts", sub: "util", accent: "#84cc16" },
  ];
  const edges: Array<[number, number]> = [
    [0, 1], [0, 2], [1, 3], [1, 4], [2, 5], [2, 6], [5, 4], [3, 4],
  ];

  return (
    <div className="p-3 sm:p-5">
      <svg
        viewBox="0 0 600 310"
        className="w-full h-auto block"
        role="img"
        aria-label="Illustration of a DevPilot dependency graph connecting app entry point to modules, services, classes, functions and routes"
      >
        {edges.map(([a, b], i) => (
          <line
            key={i}
            x1={nodes[a].x}
            y1={nodes[a].y + 22}
            x2={nodes[b].x}
            y2={nodes[b].y - 22}
            stroke={subFill}
            strokeOpacity={0.35}
            strokeWidth={1.5}
          />
        ))}
        {nodes.map((n) => (
          <g key={n.label}>
            <rect
              x={n.x - 62}
              y={n.y - 22}
              width={124}
              height={44}
              rx={10}
              fill={nodeFill}
              stroke={n.accent}
              strokeOpacity={0.55}
              strokeWidth={1.5}
              strokeDasharray={undefined}
            />
            <circle cx={n.x - 47} cy={n.y} r={4} fill={n.accent} />
            <text x={n.x - 36} y={n.y - 1} fontSize={13} fontWeight={600} fill={labelFill}>
              {n.label}
            </text>
            <text x={n.x - 36} y={n.y + 13} fontSize={10} fill={subFill}>
              {n.sub}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
