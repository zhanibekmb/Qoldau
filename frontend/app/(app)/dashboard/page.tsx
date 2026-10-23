"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CategoryChip, PriorityBadge, StatusBadge } from "@/components/badges";
import { Guard } from "@/components/Guard";
import { Card, Empty, Spinner } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRealtimeEvent } from "@/lib/realtime";
import type { Page, RequestCard } from "@/lib/types";

const OPEN = ["Submitted", "Classified", "Routed", "In Progress", "Needs Review", "Reopened", "Waiting for Student"];

function Dashboard() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [stats, setStats] = useState<{ open: number; waiting: number; resolved: number } | null>(null);
  const [recent, setRecent] = useState<RequestCard[] | null>(null);

  const load = useCallback(async () => {
    const count = (status: string[]) => api<Page<RequestCard>>(`/requests${qs({ status, page_size: 1 })}`).then((p) => p.total);
    const [open, waiting, resolved, list] = await Promise.all([
      count(OPEN),
      count(["Waiting for Student"]),
      count(["Resolved", "Closed"]),
      api<Page<RequestCard>>(`/requests${qs({ page_size: 5 })}`),
    ]);
    setStats({ open, waiting, resolved });
    setRecent(list.items);
  }, []);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);
  useRealtimeEvent((e) => e.event === "status_changed" && load().catch(() => {}));

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("dash.welcome", { name: user?.name.split(" ")[0] ?? "" })}</h1>
          <p className="mt-1 text-muted">{t("dash.cta")}</p>
        </div>
        <Link
          href="/requests/new"
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-md bg-primary px-5 font-semibold text-primary-fg hover:bg-primary/90"
        >
          <Plus className="h-5 w-5" aria-hidden />
          {t("nav.newRequest")}
        </Link>
      </div>
      <dl className="grid gap-2 sm:grid-cols-3 sm:gap-3">
        {[
          ["dash.open", stats?.open],
          ["dash.waiting", stats?.waiting],
          ["dash.resolved", stats?.resolved],
        ].map(([k, v]) => (
          <Card key={k as string} className="flex items-center justify-between gap-3 px-4 py-3 sm:block sm:p-4">
            <dt className="text-sm text-muted">{t(k as string)}</dt>
            <dd className="text-2xl font-bold tabular-nums sm:mt-1 sm:text-3xl">{v ?? "–"}</dd>
          </Card>
        ))}
      </dl>
      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">{t("dash.recent")}</h2>
          <Link href="/requests" className="text-sm font-semibold text-primary hover:underline">
            {t("nav.myRequests")}
          </Link>
        </div>
        {!recent ? (
          <Spinner />
        ) : recent.length === 0 ? (
          <Empty>{t("common.none")}</Empty>
        ) : (
          <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
            {recent.map((r) => (
              <li key={r.id}>
                <Link href={`/requests/${r.id}`} className="block px-4 py-3.5 hover:bg-surface-2">
                  <div className="flex items-start justify-between gap-3">
                    <p className="min-w-0 break-words font-semibold">{r.subject}</p>
                    <StatusBadge status={r.status} />
                  </div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-muted">
                    <span className="tabular-nums">{r.id}</span>
                    <PriorityBadge priority={r.priority} />
                    <CategoryChip name={r.category?.name} />
                    <span className="ml-auto">{timeAgo(r.created_at)}</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Guard roles={["student"]}>
      <Dashboard />
    </Guard>
  );
}
