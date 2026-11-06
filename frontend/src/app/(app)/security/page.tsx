import type { Metadata } from "next";
import { SecurityView } from "@/features/security/SecurityView";

export const metadata: Metadata = {
  title: "Security & Dependencies — DevPilot",
};

export default function SecurityPage() {
  return <SecurityView />;
}
