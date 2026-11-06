import type { Metadata } from "next";
import { CodeExplorerView } from "@/features/code-explorer/CodeExplorerView";

export const metadata: Metadata = {
  title: "Code Explorer — DevPilot",
};

export default function CodeExplorerPage() {
  return (
    <div className="h-full">
      <CodeExplorerView />
    </div>
  );
}
