"use client";

import clsx from "clsx";
import { AlertTriangle, ArrowDown, ArrowUp, Equal, PauseCircle, Timer } from "lucide-react";
import { useEffect, useState } from "react";
import { fmtDuration } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Priority, SLAState } from "@/lib/types";
import { Badge } from "./ui";

const PRIO_CLS: Record<Priority, string> = {
  Critical: "bg-critical text-white",
  High: "bg-high/12 text-high",
  Medium: "bg-medium/12 text-medium",
  Low: "bg-low/12 text-low",
};
const PRIO_ICON = { Critical: AlertTriangle, High: ArrowUp, Medium: Equal, Low: ArrowDown };

export function PriorityBadge({ priority, score }: { priority: Priority; score?: number }) {
  const { t } = useI18n();
  const Icon = PRIO_ICON[priority];
  return (
    <Badge className={PRIO_CLS[priority]} title={score !== undefined ? `Score ${score}/100` : undefined}>
      <Icon className="h-3 w-3" aria-hidden />
      {t(`prio.${priority}`)}
    </Badge>
  );
}

const STATUS_CLS: Record<string, string> = {
  Submitted: "bg-surface-2 text-muted",
  Classified: "bg-surface-2 text-muted",
  Routed: "bg-surface-2 text-text",
  "In Progress": "bg-primary-soft text-primary",
  "Waiting for Student": "bg-warn/12 text-warn",
  Resolved: "bg-ok/12 text-ok",
  Closed: "bg-surface-2 text-muted",
  "Needs Review": "bg-warn/12 text-warn",
  Reopened: "bg-high/12 text-high",
};

export function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  return <Badge className={STATUS_CLS[status] ?? "bg-surface-2"}>{t(`status.${status}`)}</Badge>;
}

export function CategoryChip({ name }: { name?: string | null }) {
  if (!name) return null;
  return <Badge className="bg-surface-2 text-text">{name}</Badge>;
}

const SLA_CLS = {
  green: "bg-ok/12 text-ok",
  yellow: "bg-medium/12 text-medium",
  red: "bg-critical/12 text-critical",
  black: "bg-black text-white dark:bg-white dark:text-black",
};

/** Countdown badge: green > 50% left, yellow 20-50%, red < 20%, black = breached (US12). */
export function SlaBadge({ sla }: { sla: SLAState | null }) {
  const { t } = useI18n();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!sla || sla.paused) return;
    const id = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(id);
  }, [sla]);
  if (!sla) return null;
  if (sla.paused)
    return (
      <Badge className="bg-surface-2 text-muted">
        <PauseCircle className="h-3 w-3" aria-hidden />
        {t("sla.paused")}
      </Badge>
    );
  const remaining = (new Date(sla.due_at).getTime() - now) / 1000;
  const breached = sla.breached || remaining <= 0;
  const total = sla.remaining_fraction > 0 ? sla.remaining_seconds / sla.remaining_fraction : 0;
  const frac = total ? remaining / total : 0;
  const color = breached ? "black" : frac <= 0.2 ? "red" : frac <= 0.5 ? "yellow" : "green";
  return (
    <Badge className={clsx(SLA_CLS[color])} title={`${sla.target === "first_response" ? "First response" : "Resolution"} due ${new Date(sla.due_at).toLocaleString()}`}>
      <Timer className="h-3 w-3" aria-hidden />
      {breached ? t("sla.breached") : t("sla.left", { t: fmtDuration(remaining) })}
    </Badge>
  );
}
