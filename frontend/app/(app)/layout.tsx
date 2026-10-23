import { Suspense } from "react";
import { AppShell } from "@/components/AppShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  // AppShell reads the URL (usePathname), so it streams in behind a Suspense boundary.
  return (
    <Suspense>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
