import type { Metadata } from "next";
import { CommandCenterView } from "@/features/command-center/CommandCenterView";

export const metadata: Metadata = {
  title: "Command Center — DevPilot",
};

export default function CommandCenterPage() {
  return <CommandCenterView />;
}
