"use client";

import { Guard } from "@/components/Guard";
import { RequestList } from "@/components/RequestList";
import { useI18n } from "@/lib/i18n";

export default function TriagePage() {
  const { t } = useI18n();
  return (
    <Guard roles={["agent", "unit_head", "admin"]}>
      <h1 className="mb-1 text-2xl font-bold">{t("nav.triage")}</h1>
      <p className="mb-4 text-sm text-muted">
        Requests the AI could not classify with at least 60% confidence. Open one and confirm the category to route it.
      </p>
      <RequestList staff view="triage" />
    </Guard>
  );
}
