"use client";

import clsx from "clsx";
import { BookOpen, CheckCircle2, ChevronDown, Lightbulb, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { SimilarOut, SuggestionItem } from "@/lib/types";
import { SafeHtml } from "./RichText";
import { Button } from "./ui";

const MIN_CHARS = 15;
const DEBOUNCE_MS = 500;

/**
 * "Maybe this helps" (US20): FAQ answers and anonymised solved requests while the student types.
 * It never blocks submission; "This solved my problem" ends the flow without creating a request.
 */
export function SuggestPanel({
  subject,
  description,
  sessionId,
  onDeflect,
}: {
  subject: string;
  description: string;
  sessionId: string;
  onDeflect: () => void;
}) {
  const { t } = useI18n();
  const [data, setData] = useState<SimilarOut | null>(null);
  const [open, setOpen] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [voted, setVoted] = useState<Record<string, boolean>>({});
  const logged = useRef(new Set<string>());

  const log = (type: "faq" | "similar", ids: string[], action: string) =>
    ids.length && api("/suggestions/events", { method: "POST", json: { session_id: sessionId, type, item_ids: ids, action } }).catch(() => {});

  useEffect(() => {
    if (description.trim().length < MIN_CHARS) {
      setData(null);
      return;
    }
    const id = setTimeout(() => {
      api<SimilarOut>("/ai/similar", { method: "POST", json: { text: `${subject}\n${description}`.trim().slice(0, 2000) } })
        .then((out) => {
          setData(out);
          for (const [type, items] of [["faq", out.faq], ["similar", out.cases]] as const) {
            const fresh = items.map((i) => i.id).filter((i) => !logged.current.has(i));
            fresh.forEach((i) => logged.current.add(i));
            log(type, fresh, "shown");
          }
        })
        .catch(() => setData(null));
    }, DEBOUNCE_MS);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subject, description]);

  if (!data || (data.faq.length === 0 && data.cases.length === 0)) return null;

  const toggle = (item: SuggestionItem) => {
    const next = expanded === item.id ? null : item.id;
    setExpanded(next);
    if (next && item.source === "faq") log("faq", [item.id], "opened");
  };
  const vote = (item: SuggestionItem, helpful: boolean) => {
    setVoted((v) => ({ ...v, [item.id]: helpful }));
    api(`/faq/${item.id.split(":")[1]}/vote`, { method: "POST", json: { helpful } }).catch(() => {});
  };
  const solved = async (item: SuggestionItem) => {
    await log(item.source === "faq" ? "faq" : "similar", [item.id], "deflected");
    onDeflect();
  };

  return (
    <section aria-labelledby="sug-title" className="rounded-md border border-primary/30 bg-primary-soft/40">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="sug-body"
        className="flex min-h-11 w-full items-center gap-2 px-4 py-2 text-left"
      >
        <Lightbulb className="h-5 w-5 shrink-0 text-primary" aria-hidden />
        <span id="sug-title" className="font-semibold">
          {t("sug.title")}
        </span>
        <span className="text-sm text-muted">({data.faq.length + data.cases.length})</span>
        <ChevronDown className={clsx("ml-auto h-5 w-5 text-muted transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open && (
        <div id="sug-body" className="space-y-4 px-4 pb-4" aria-live="polite">
          <p className="text-sm text-muted">{t("sug.intro")}</p>
          {data.faq.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t("sug.faq")}</h3>
              <ul className="space-y-2">
                {data.faq.map((item) => (
                  <li key={item.id} className="rounded-md border border-border bg-surface p-3">
                    <div className="flex items-start gap-2">
                      <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium">{item.title}</div>
                        {item.unit && <div className="text-xs text-muted">{item.unit}</div>}
                        {expanded !== item.id && <p className="mt-1 text-sm text-muted">{item.snippet}</p>}
                      </div>
                    </div>
                    {expanded === item.id && item.body && (
                      <div className="mt-2 border-t border-border pt-2 text-sm">
                        <SafeHtml html={item.body} />
                        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                          {item.id in voted ? (
                            <span className="text-muted">{t("sug.thanks")}</span>
                          ) : (
                            <>
                              <span className="text-muted">{t("sug.helpful")}</span>
                              <Button type="button" size="sm" variant="ghost" onClick={() => vote(item, true)}>
                                <ThumbsUp className="h-4 w-4" aria-hidden /> {t("sug.yes")}
                              </Button>
                              <Button type="button" size="sm" variant="ghost" onClick={() => vote(item, false)}>
                                <ThumbsDown className="h-4 w-4" aria-hidden /> {t("sug.no")}
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button type="button" size="sm" variant="secondary" aria-expanded={expanded === item.id} onClick={() => toggle(item)}>
                        {expanded === item.id ? t("sug.hide") : t("sug.read")}
                      </Button>
                      <Button type="button" size="sm" variant="ghost" className="text-ok" onClick={() => solved(item)}>
                        <CheckCircle2 className="h-4 w-4" aria-hidden /> {t("sug.solved")}
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {data.cases.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t("sug.cases")}</h3>
              <ul className="space-y-2">
                {data.cases.map((item) => (
                  <li key={item.id} className="rounded-md border border-border bg-surface p-3 text-sm">
                    <div className="font-medium">{item.title}</div>
                    <p className="mt-1">
                      <span className="text-muted">{t("sug.solvedHow")}: </span>
                      {item.snippet}
                    </p>
                    <Button type="button" size="sm" variant="ghost" className="mt-1 text-ok" onClick={() => solved(item)}>
                      <CheckCircle2 className="h-4 w-4" aria-hidden /> {t("sug.solved")}
                    </Button>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted">{t("sug.anonymised")}</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
