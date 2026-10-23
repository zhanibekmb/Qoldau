"use client";

import clsx from "clsx";
import { AlertTriangle, Cpu, Flag, Lock, MessageSquare, Send, Share2, Star, StepForward } from "lucide-react";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { TimelineEvent } from "@/lib/types";

const ICONS = {
  submitted: Send,
  status: Flag,
  ai: Cpu,
  routing: Share2,
  message: MessageSquare,
  note: Lock,
  escalation: AlertTriangle,
  step: StepForward,
  csat: Star,
};

/** Vertical request timeline (US11): every event with timestamp and actor. */
export function Timeline({ events }: { events: TimelineEvent[] }) {
  const { t, lang } = useI18n();
  return (
    <ol className="relative space-y-4 border-l-2 border-border pl-6">
      {events.map((e) => {
        const Icon = ICONS[e.kind] ?? Flag;
        return (
          <li key={e.id} className="relative">
            <span
              className={clsx(
                "absolute -left-[37px] grid h-8 w-8 place-items-center rounded-full border-2 border-surface",
                e.kind === "note" && "bg-yellow-400 text-black",
                e.kind === "escalation" && "bg-critical text-white",
                e.kind === "ai" && "bg-primary-soft text-primary",
                !["note", "escalation", "ai"].includes(e.kind) && "bg-surface-2 text-muted",
              )}
              aria-hidden
            >
              <Icon className="h-4 w-4" />
            </span>
            <div className={clsx("rounded-md px-3 py-2", e.kind === "note" && "bg-yellow-400/15")}>
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-semibold">{e.status ? t(`status.${e.status}`) : e.title}</span>
                <time className="text-xs text-muted" dateTime={e.created_at}>
                  {fmtDate(e.created_at, lang)}
                </time>
                {e.actor && <span className="text-xs text-muted">· {e.actor}</span>}
              </div>
              {e.detail && <p className="mt-0.5 whitespace-pre-wrap break-words text-sm text-muted">{e.detail}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
