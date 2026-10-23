"use client";

import { BookOpen, Copy, FileText, History, RefreshCw, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { RequestDetail, SmartReply } from "@/lib/types";
import { Badge, Button, Card, Spinner, Toast } from "./ui";

const SOURCE_ICON = { template: FileText, similar_case: History, kb: BookOpen };

export function logSmartReply(requestId: string, sourceId: string, action: "used" | "edited" | "ignored") {
  api("/suggestions/events", { method: "POST", json: { request_id: requestId, type: "smart_reply", item_ids: [sourceId], action } }).catch(() => {});
}

/** Smart Reply panel (US19): top-3 suggestions; Insert puts text in the reply box, never sends it. */
export function SmartReplies({ requestId, refreshKey, onInsert }: { requestId: string; refreshKey: number; onInsert: (s: SmartReply) => void }) {
  const { t } = useI18n();
  const [items, setItems] = useState<SmartReply[] | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState<string | null>(null);

  const load = useCallback(() => {
    api<{ suggestions: SmartReply[] }>(`/ai/suggestions/${requestId}`)
      .then((r) => setItems(r.suggestions))
      .catch(() => setItems([]));
  }, [requestId]);

  useEffect(load, [load, refreshKey]);

  const visible = (items ?? []).filter((s) => !hidden.has(s.source_id));

  return (
    <Card>
      <div className="mb-1 flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-primary" aria-hidden />
        <h2 className="font-semibold">{t("sr.title")}</h2>
        <button onClick={load} aria-label={t("common.refresh")} title={t("common.refresh")} className="ml-auto grid h-11 w-11 place-items-center rounded-md text-muted hover:bg-surface-2">
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
      <p className="mb-3 text-xs text-muted">{t("sr.hint")}</p>
      {items === null ? (
        <Spinner />
      ) : visible.length === 0 ? (
        <p className="text-sm text-muted">{t("sr.none")}</p>
      ) : (
        <ul className="space-y-3">
          {visible.map((s) => {
            const Icon = SOURCE_ICON[s.source];
            return (
              <li key={s.source_id} className="rounded-md border border-border p-3">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                  <Badge className="bg-primary-soft text-primary">
                    <Icon className="h-3 w-3" aria-hidden /> {t(`sr.src.${s.source}`)}
                  </Badge>
                  <span className="text-muted">{t("sr.relevance", { v: Math.round(Math.min(1, s.score) * 100) })}</span>
                </div>
                <div className="text-sm font-medium">{s.title}</div>
                <p className="mt-1 line-clamp-4 whitespace-pre-line text-sm text-muted">{s.text}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  <Button size="sm" onClick={() => onInsert(s)}>
                    {t("sr.insert")}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    aria-label={t("sr.copy")}
                    onClick={() => {
                      navigator.clipboard?.writeText(s.text).catch(() => {});
                      setCopied(s.source_id);
                      logSmartReply(requestId, s.source_id, "used");
                    }}
                  >
                    <Copy className="h-4 w-4" aria-hidden /> {copied === s.source_id ? t("sr.copied") : t("sr.copy")}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label={t("sr.dismiss")}
                    onClick={() => {
                      setHidden((h) => new Set(h).add(s.source_id));
                      logSmartReply(requestId, s.source_id, "ignored");
                    }}
                  >
                    <X className="h-4 w-4" aria-hidden /> {t("sr.dismiss")}
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

/** "Propose FAQ" / "Save reply as template" on a resolved ticket (US21). */
export function KbActions({ req }: { req: RequestDetail }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; tone: "info" | "error" } | null>(null);

  async function run(kind: "propose-faq" | "save-template") {
    setBusy(kind);
    try {
      await api(`/requests/${req.id}/${kind}`, { method: "POST", json: {} });
      setToast({ msg: kind === "propose-faq" ? t("kb.proposed") : t("kb.templateSaved"), tone: "info" });
    } catch (err) {
      setToast({ msg: err instanceof ApiError ? err.message : t("common.error"), tone: "error" });
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <h2 className="flex items-center gap-2 font-semibold">
        <BookOpen className="h-5 w-5 text-primary" aria-hidden /> {t("nav.kb")}
      </h2>
      <p className="mb-3 mt-1 text-xs text-muted">{t("kb.ticketHint")}</p>
      <div className="flex flex-col gap-2">
        <Button variant="secondary" loading={busy === "propose-faq"} onClick={() => run("propose-faq")}>
          {t("kb.propose")}
        </Button>
        <Button variant="secondary" loading={busy === "save-template"} onClick={() => run("save-template")}>
          {t("kb.saveTemplate")}
        </Button>
        <Link href="/kb" className="inline-flex min-h-11 items-center justify-center text-sm font-semibold text-primary">
          {t("nav.kb")} →
        </Link>
      </div>
      {toast && <Toast message={toast.msg} tone={toast.tone} onDone={() => setToast(null)} />}
    </Card>
  );
}
