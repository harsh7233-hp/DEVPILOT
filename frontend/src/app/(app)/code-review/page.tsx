import type { Metadata } from "next";
import { CodeReviewView } from "@/features/code-review/CodeReviewView";

export const metadata: Metadata = {
  title: "Code Review — DevPilot",
};

export default function CodeReviewPage() {
  return <CodeReviewView />;
}
