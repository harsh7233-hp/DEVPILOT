import type { Metadata } from "next";
import { PipelinesView } from "@/features/pipelines/PipelinesView";

export const metadata: Metadata = {
  title: "Pipelines — DevPilot",
};

export default function PipelinesPage() {
  return <PipelinesView />;
}
