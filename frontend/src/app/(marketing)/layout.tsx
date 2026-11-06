import type { Metadata } from "next";
import { ThemeProvider } from "@/lib/theme-context";

export const metadata: Metadata = {
  title: "DevPilot -- AI-Powered Developer Platform",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
