import type { Metadata } from "next";
import { RepositoriesView } from "@/features/repositories/RepositoriesView";

export const metadata: Metadata = {
  title: "Repositories — DevPilot",
};

export default function RepositoriesPage() {
  return <RepositoriesView />;
}
