"use client";

import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { RequestCard } from "@/lib/types";

export function StudentNextStep({ request }: { request: RequestCard }) {
  const { lang, t } = useI18n();
  const step = {
    "Waiting for Student": "pilot.nextReply",
    Resolved: "pilot.nextResolved",
    Closed: "pilot.nextClosed",
  } as const;
  const instruction = step[request.status as keyof typeof step] ?? (request.unit ? "pilot.nextWait" : "pilot.nextReview");
  const due = request.sla;

  return (
    <div className="min-w-0 rounded-md border border-border bg-surface px-3 py-2.5 text-left text-sm">
      <p className="font-semibold">{t("pilot.nextStep")}</p>
      <p className="mt-0.5 text-muted">{t(instruction)}</p>
      {due && !due.paused && !due.breached && (
        <p className="mt-1.5 font-medium">
          {t(due.target === "first_response" ? "pilot.replyDue" : "pilot.resolutionDue", { date: fmtDate(due.due_at, lang, true) })}
        </p>
      )}
    </div>
  );
}
