"use client";

import clsx from "clsx";
import { AlertCircle, Archive, Check, CheckCircle2, Cpu, Send, Share2, Wrench } from "lucide-react";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { TimelineEvent } from "@/lib/types";

const STAGES = [
  { status: "Submitted", icon: Send },
  { status: "Classified", icon: Cpu },
  { status: "Routed", icon: Share2 },
  { status: "In Progress", icon: Wrench },
  { status: "Resolved", icon: CheckCircle2 },
  { status: "Closed", icon: Archive },
];

const STAGE_INDEX: Record<string, number> = {
  Submitted: 0,
  Classified: 1,
  "Needs Review": 1,
  Routed: 2,
  "In Progress": 3,
  "Waiting for Student": 3,
  Reopened: 3,
  Resolved: 4,
  Closed: 5,
};

/** Step-by-step progress bar (US2). Horizontal from 768px, vertical below so nothing overlaps. */
export function ProgressTracker({ status, events }: { status: string; events: TimelineEvent[] }) {
  const { t, lang } = useI18n();
  const current = STAGE_INDEX[status] ?? 0;
  const attention = status === "Waiting for Student" ? t("detail.actionRequired") : status === "Needs Review" ? t("detail.underReview") : null;

  const reachedAt = (stage: string) => {
    const hit = [...events].reverse().find((e) => (stage === "Submitted" ? e.kind === "submitted" : e.status === stage));
    return hit?.created_at;
  };

  return (
    <ol aria-label={t("detail.progress")} className="flex flex-col gap-0 md:flex-row md:items-start">
      {STAGES.map((s, i) => {
        const done = i < current;
        const active = i === current;
        const warn = active && !!attention;
        const Icon = done ? Check : warn ? AlertCircle : s.icon;
        const at = i <= current ? reachedAt(s.status) : undefined;
        return (
          <li
            key={s.status}
            aria-current={active ? "step" : undefined}
            className={clsx("relative flex min-w-0 flex-1 gap-3 pb-6 md:flex-col md:items-center md:pb-0 md:text-center", !done && !active && "opacity-45")}
          >
            {i < STAGES.length - 1 && (
              <span
                aria-hidden
                className={clsx(
                  "absolute left-[19px] top-10 h-[calc(100%-2.5rem)] w-0.5 md:left-[calc(50%+24px)] md:top-5 md:h-0.5 md:w-[calc(100%-48px)]",
                  done ? "bg-ok" : "bg-border",
                )}
              />
            )}
            <span
              className={clsx(
                "relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-full border-2 transition-colors duration-500",
                done && "border-ok bg-ok text-white",
                active && !warn && "border-primary bg-primary text-primary-fg",
                warn && "border-warn bg-warn text-white",
                !done && !active && "border-border bg-surface text-muted",
              )}
            >
              <Icon className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0 md:mt-2 md:px-1">
              <div className={clsx("text-sm", active ? "font-bold" : "font-medium")}>
                {active && status !== s.status && !warn ? t(`status.${status}`) : t(`status.${s.status}`)}
              </div>
              {warn && <div className="text-xs font-semibold text-warn">{attention}</div>}
              {at && <div className="text-xs text-muted">{fmtDate(at, lang)}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
