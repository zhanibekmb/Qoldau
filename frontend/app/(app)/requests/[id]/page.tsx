"use client";

import { AlertTriangle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { CategoryChip, PriorityBadge, SlaBadge, StatusBadge } from "@/components/badges";
import { Chat } from "@/components/Chat";
import { CsatCard, Stars } from "@/components/Csat";
import { ProgressTracker } from "@/components/ProgressTracker";
import { KbActions, logSmartReply, SmartReplies } from "@/components/SmartReplies";
import { AiPanel, Highlighted, StaffActions } from "@/components/StaffPanel";
import { Timeline } from "@/components/Timeline";
import { Card, Empty, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { isStaff, useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { RtEvent } from "@/lib/realtime";
import type { RequestDetail, SmartReply, TimelineEvent } from "@/lib/types";

export default function RequestPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const [req, setReq] = useState<RequestDetail | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [error, setError] = useState("");
  const [insert, setInsert] = useState<{ text: string; key: number }>();
  const [replyKey, setReplyKey] = useState(0);
  const inserted = useRef<SmartReply | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, tl] = await Promise.all([
        api<RequestDetail>(`/requests/${id}`),
        api<TimelineEvent[]>(`/requests/${id}/timeline`),
      ]);
      setReq(r);
      setEvents(tl);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 404 ? "Request not found" : t("common.error"));
    }
  }, [id, t]);

  useEffect(() => {
    load();
  }, [load]);

  // Live updates without page refresh (US2): status changes, steps, re-routing, CSAT.
  const onEvent = useCallback(
    (e: RtEvent) => {
      if (["status_changed", "request_updated", "step_changed", "csat", "message"].includes(e.event)) load();
      if (e.event === "message" && !e.internal) setReplyKey((k) => k + 1); // smart replies follow the conversation
    },
    [load],
  );

  const onInsert = useCallback((s: SmartReply) => {
    inserted.current = s;
    setInsert({ text: s.text, key: Date.now() });
  }, []);

  // A suggestion sent unchanged counts as "used", sent after changes as "edited" (US19 usefulness).
  const onSent = useCallback(
    (body: string, internal: boolean) => {
      const s = inserted.current;
      if (!s || internal) return;
      logSmartReply(id, s.source_id, body.trim() === s.text.trim() ? "used" : "edited");
      inserted.current = null;
    },
    [id],
  );

  if (error) return <Empty>{error}</Empty>;
  if (!req || !user) return <Spinner label={t("common.loading")} />;
  const staff = isStaff(user);

  return (
    <div className="space-y-5">
      <Link href={staff ? "/agent/board" : "/requests"} className="inline-flex min-h-11 items-center gap-1 text-sm text-muted hover:text-text">
        <ArrowLeft className="h-4 w-4" /> {staff ? t("nav.board") : t("nav.myRequests")}
      </Link>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm tabular-nums text-muted">{req.id}</p>
          <h1 className="mt-0.5 break-words text-2xl font-bold">{req.subject}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={req.status} />
            <PriorityBadge priority={req.priority} score={staff ? req.priority_score : undefined} />
            <CategoryChip name={req.category?.name} />
            {staff && <SlaBadge sla={req.sla} />}
            {req.escalated && staff && (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-critical">
                <AlertTriangle className="h-3.5 w-3.5" /> Escalated
              </span>
            )}
          </div>
        </div>
        <dl className="grid shrink-0 grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted">{t("detail.unit")}</dt>
          <dd>{req.unit?.name ?? "—"}</dd>
          <dt className="text-muted">{t("detail.assignee")}</dt>
          <dd>{req.assignee?.name ?? t("common.unassigned")}</dd>
          <dt className="text-muted">{t("detail.created")}</dt>
          <dd>{fmtDate(req.created_at, lang)}</dd>
          {staff && req.student && (
            <>
              <dt className="text-muted">Student</dt>
              <dd>{req.student.name}</dd>
            </>
          )}
        </dl>
      </div>

      <Card>
        <h2 className="sr-only">{t("detail.progress")}</h2>
        <ProgressTracker status={req.status} events={events} />
        {req.workflow_steps.length > 0 && (
          <p className="mt-4 text-sm text-muted">
            {req.workflow_steps.map((s, i) => (
              <span key={s} className={i === req.workflow_step ? "font-semibold text-primary" : i < req.workflow_step ? "text-ok" : ""}>
                {i > 0 && " → "}
                {s}
              </span>
            ))}
          </p>
        )}
      </Card>

      {!staff && req.status === "Resolved" && !req.csat && <CsatCard requestId={req.id} onDone={load} />}
      {req.csat && (
        <Card className="flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium">{t("csat.your")}</span>
          <Stars value={req.csat.rating} size="h-5 w-5" />
          {req.csat.comment && <span className="text-sm text-muted">“{req.csat.comment}”</span>}
        </Card>
      )}

      <div className={staff ? "grid gap-5 lg:grid-cols-[1fr_360px]" : "grid gap-5"}>
        <div className="min-w-0 space-y-5">
          <Card>
            <h2 className="mb-2 text-lg font-semibold">{t("detail.description")}</h2>
            <p className="whitespace-pre-wrap break-words leading-relaxed">
              {staff && req.ai ? <Highlighted text={req.description} keywords={req.ai.keywords} /> : req.description}
            </p>
          </Card>
          <Card>
            <h2 className="mb-3 text-lg font-semibold">{t("detail.chat")}</h2>
            <Chat
              requestId={req.id}
              viewer={user}
              closed={req.status === "Closed"}
              onEvent={onEvent}
              insert={staff ? insert : undefined}
              onSent={staff ? onSent : undefined}
            />
          </Card>
          <Card>
            <h2 className="mb-4 text-lg font-semibold">{t("detail.timeline")}</h2>
            <Timeline events={events} />
          </Card>
        </div>
        {staff && (
          <div className="space-y-5">
            <StaffActions req={req} viewer={user} onChange={() => load()} />
            {req.status !== "Closed" && <SmartReplies requestId={req.id} refreshKey={replyKey} onInsert={onInsert} />}
            {(req.status === "Resolved" || req.status === "Closed") && <KbActions req={req} />}
            {req.ai && <AiPanel req={req} onChange={() => load()} />}
          </div>
        )}
      </div>
    </div>
  );
}
