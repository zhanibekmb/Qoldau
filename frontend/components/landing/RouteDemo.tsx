"use client";

import { ArrowDown, ArrowRight } from "lucide-react";
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
    <figure className="w-full max-w-md rounded-lg bg-bg p-5 sm:p-6">
      <figcaption className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-muted">
          {copy.label} {index + 1} / {DEMO_REQUESTS.length}
        </span>
        <button
          type="button"
          onClick={() => setIndex((i) => (i + 1) % DEMO_REQUESTS.length)}
          className="-mr-2 inline-flex min-h-11 items-center gap-1 rounded-md px-2 text-sm font-semibold text-primary hover:bg-surface-2"
        >
          {copy.next}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </figcaption>

      <div aria-live="polite">
        <p className="mt-4 text-sm text-muted">{copy.student}</p>
        <blockquote lang={HTML_LANG[req.lang]} className="mt-1.5 rounded-md bg-surface p-4 text-lg leading-snug">
          {req.text}
        </blockquote>

        <ArrowDown className="mx-auto my-3 h-5 w-5 text-muted" aria-hidden />

        <dl className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2.5 rounded-md bg-surface p-4 text-[15px]">
          <dt className="text-muted">{copy.routed}</dt>
          <dd className="font-semibold">{offices[req.office].name}</dd>
          <dt className="text-muted">{copy.category}</dt>
          <dd>{req.category[lang]}</dd>
          <dt className="text-muted">{copy.urgency}</dt>
          <dd>
            <PriorityBadge priority={req.priority} />
          </dd>
          <dt className="text-muted">{copy.firstResponse}</dt>
          <dd className="font-semibold">{req.first[lang]}</dd>
        </dl>
      </div>
    </figure>
  );
}
