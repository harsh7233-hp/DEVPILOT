import type { Metadata } from "next";
import { AIAssistantView } from "@/features/ai-assistant/AIAssistantView";

export const metadata: Metadata = {
  title: "AI Assistant — DevPilot",
};

export default function AIAssistantPage() {
  return (
    <div className="h-full">
      <AIAssistantView />
    </div>
  );
}
