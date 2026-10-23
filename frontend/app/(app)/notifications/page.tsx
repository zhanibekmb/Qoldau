"use client";

import clsx from "clsx";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button, Empty, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRealtime, useRealtimeEvent } from "@/lib/realtime";
import type { Notification } from "@/lib/types";

export default function NotificationsPage() {
  const { t, lang } = useI18n();
  const { setUnread } = useRealtime();
  const [items, setItems] = useState<Notification[] | null>(null);

  const load = useCallback(() => {
    api<Notification[]>("/notifications?limit=50").then(setItems).catch(() => setItems([]));
  }, []);
  useEffect(load, [load]);
  useRealtimeEvent((e) => e.event === "notification" && load());

  async function markAll() {
    const r = await api<{ count: number }>("/notifications/read", { method: "POST" });
    setUnread(r.count);
    load();
  }

  async function markOne(n: Notification) {
    if (n.is_read) return;
    const r = await api<{ count: number }>("/notifications/read", { method: "POST", json: [n.id] });
    setUnread(r.count);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("nav.notifications")}</h1>
        <Button size="sm" variant="secondary" onClick={markAll}>
          {t("notif.markAll")}
        </Button>
      </div>
      {!items ? (
        <Spinner />
      ) : items.length === 0 ? (
        <Empty>{t("notif.empty")}</Empty>
      ) : (
        <ul className="space-y-2">
          {items.map((n) => {
            const body = (
              <div className={clsx("rounded-lg border p-4", n.is_read ? "border-border bg-surface" : "border-primary/30 bg-primary-soft")}>
                <div className="flex items-start justify-between gap-2">
                  <p className={clsx("break-words text-sm", !n.is_read && "font-semibold")}>{n.title}</p>
                  {!n.is_read && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
                </div>
                {n.body && <p className="mt-0.5 break-words text-sm text-muted">{n.body}</p>}
                <p className="mt-1 text-xs text-muted">{fmtDate(n.created_at, lang)}</p>
              </div>
            );
            return (
              <li key={n.id}>
                {n.request_id ? (
                  <Link href={`/requests/${n.request_id}`} onClick={() => markOne(n)} className="block">
                    {body}
                  </Link>
                ) : (
                  body
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
