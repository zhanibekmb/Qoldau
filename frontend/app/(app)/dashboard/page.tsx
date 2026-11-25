"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CategoryChip, PriorityBadge, StatusBadge } from "@/components/badges";
import { Guard } from "@/components/Guard";
import { Spinner } from "@/components/ui";
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

  const metrics = [
    { label: t("dash.open"), value: stats?.open },
    { label: t("dash.waiting"), value: stats?.waiting },
    { label: t("dash.resolved"), value: stats?.resolved },
  ];

  return (
    <div className="space-y-4 sm:space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <h1 className="min-w-0 text-xl font-semibold sm:text-2xl">{t("dash.welcome", { name: user?.name.split(" ")[0] ?? "" })}</h1>
        <Link
          href="/requests/new"
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-1.5 rounded-md bg-primary px-3 text-sm font-semibold text-primary-fg hover:bg-primary/90 md:min-h-9"
        >
          <Plus className="size-4" aria-hidden />
          {t("nav.newRequest")}
        </Link>
      </div>
      <dl className="grid grid-cols-3 divide-x divide-border rounded-lg border border-border bg-surface">
        {metrics.map(({ label, value }) => (
          <div key={label} className="flex min-w-0 flex-col gap-1 px-2.5 py-2.5 sm:px-4 sm:py-3">
            <dt className="flex-1 text-xs leading-snug text-muted sm:text-sm">{label}</dt>
            <dd className="text-[1.375rem] leading-tight font-semibold tabular-nums sm:text-2xl">{value ?? "–"}</dd>
          </div>
        ))}
      </dl>
      <section className="rounded-lg border border-border bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-x-3 border-b border-border px-3 sm:px-4">
          <h2 className="text-[15px] font-semibold">{t("dash.recent")}</h2>
          <Link href="/requests" className="inline-flex min-h-11 items-center text-sm font-medium text-primary hover:underline md:min-h-9">
            {t("nav.myRequests")}
          </Link>
        </div>
        {!recent ? (
          <Spinner label={t("common.loading")} />
        ) : recent.length === 0 ? (
          <p className="px-3 py-4 text-sm text-muted sm:px-4">{t("common.none")}</p>
        ) : (
          <ul className="divide-y divide-border">
            {recent.map((r) => (
              <li key={r.id}>
                <Link href={`/requests/${r.id}`} className="block px-3 py-2.5 hover:bg-surface-2 focus-visible:outline-offset-[-2px] sm:px-4">
                  <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                    <p className="min-w-0 break-words text-sm font-semibold">{r.subject}</p>
                    <StatusBadge status={r.status} />
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
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
