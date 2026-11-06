import type { Metadata } from "next";
import { ImpactAnalysisView } from "@/features/impact-analysis/ImpactAnalysisView";

export const metadata: Metadata = {
  title: "Impact Analysis — DevPilot",
};

export default function ImpactAnalysisPage() {
  return <ImpactAnalysisView />;
}
