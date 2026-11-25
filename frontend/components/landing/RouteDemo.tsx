"use client";

import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { PriorityBadge } from "@/components/badges";
import { DEMO_REQUESTS, type LandingCopy } from "@/lib/landing-copy";
import type { Lang } from "@/lib/types";

const HTML_LANG = { KZ: "kk", RU: "ru", EN: "en" } as const;

/** Hero example: a real student message and where Qoldau sends it. The visitor steps through examples. */
export function RouteDemo({ copy, offices, lang }: { copy: LandingCopy["demo"]; offices: LandingCopy["offices"]["units"]; lang: Lang }) {
  const [index, setIndex] = useState(0);
  const req = DEMO_REQUESTS[index];

  return (
    <figure className="min-w-0 rounded-xl border border-border bg-surface text-text">
      <figcaption className="flex min-h-12 items-center justify-between gap-3 border-b border-border px-4 sm:px-5">
        <span className="text-sm font-semibold text-muted">
          {copy.label} {index + 1} / {DEMO_REQUESTS.length}
        </span>
        <button
          type="button"
          onClick={() => setIndex((i) => (i + 1) % DEMO_REQUESTS.length)}
          className="-mr-2 inline-flex min-h-11 items-center gap-1.5 rounded-md px-2 text-sm font-semibold text-primary hover:bg-surface-2"
        >
          {copy.next}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </figcaption>

      <div aria-live="polite" className="grid gap-2.5 p-4 sm:p-5">
        <div className="min-w-0 rounded-lg bg-bg px-3.5 py-3">
          <p className="text-sm text-muted">{copy.student}</p>
          <blockquote lang={HTML_LANG[req.lang]} className="mt-2 text-base leading-snug sm:text-lg">
            {req.text}
          </blockquote>
        </div>

        <ArrowRight className="mx-auto size-4 rotate-90 text-muted" aria-hidden />

        <dl className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] items-start gap-x-3 gap-y-1.5 rounded-lg bg-primary-soft px-3.5 py-3 text-sm">
          <dt className="text-muted">{copy.routed}</dt>
          <dd className="font-semibold">{offices[req.office].name}</dd>
          <dt className="text-muted">{copy.category}</dt>
          <dd>{req.category[lang]}</dd>
          <dt className="text-muted">{copy.urgency}</dt>
          <dd>
            <PriorityBadge priority={req.priority} />
          </dd>
        </dl>
      </div>
    </figure>
  );
}
