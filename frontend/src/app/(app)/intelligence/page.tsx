import type { Metadata } from "next";
import { CodeIntelligenceView } from "@/features/intelligence/CodeIntelligenceView";

export const metadata: Metadata = {
  title: "Code Intelligence — DevPilot",
};

export default function IntelligencePage() {
  return <CodeIntelligenceView />;
}
