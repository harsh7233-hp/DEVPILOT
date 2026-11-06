import type { Metadata } from "next";
import { AppLayout } from "@/components/layout/AppLayout";
import { AuthProvider } from "@/lib/auth-context";
import { ThemeProvider } from "@/lib/theme-context";
import { RepoProvider } from "@/lib/repo-context";
import { NotificationProvider } from "@/lib/notification-context";

export const metadata: Metadata = {
  title: "DevPilot",
};

export default function AppRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <RepoProvider>
          <NotificationProvider>
            <AppLayout>{children}</AppLayout>
          </NotificationProvider>
        </RepoProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
