"use client";

import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { Role } from "@/lib/types";

/** Client-side role gate; the API enforces the same rules (HTTP 403). */
export function Guard({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  const { t } = useI18n();
  if (!user) return null;
  if (!roles.includes(user.role))
    return (
      <div role="alert" className="rounded-lg bg-critical/10 p-6 text-center font-semibold text-critical">
        {t("access.denied")}
      </div>
    );
  return <>{children}</>;
}
