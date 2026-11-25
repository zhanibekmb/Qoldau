"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, qs } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRealtimeEvent } from "@/lib/realtime";
import type { CategoryMeta, Page, RequestCard } from "@/lib/types";
import { CategoryChip, PriorityBadge, SlaBadge, StatusBadge } from "./badges";
import { FilterDate, FilterDialog, FilterSelect } from "./FilterDialog";
import { Button, Empty, Input, Spinner } from "./ui";

const STATUSES = ["Submitted", "Needs Review", "Routed", "In Progress", "Waiting for Student", "Resolved", "Closed", "Reopened"];
const DEFAULT_FILTERS = { status: "", category: "", priority: "", from: "", to: "" };

/** Searchable, filterable, paginated request list (US11): 20 per page. */
export function RequestList({
  view = "all",
  staff = false,
  assignee,
  onFilters,
}: {
  view?: "all" | "triage" | "escalated";
  staff?: boolean;
  assignee?: string;
  /** Reports the applied filters, e.g. for the Export menu (US17). */
  onFilters?: (f: { date_from?: string; date_to?: string; category_id?: number; priority?: string; status?: string }) => void;
}) {
  const { t, lang } = useI18n();
  const [categories, setCategories] = useState<CategoryMeta[]>([]);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const { status, category, priority, from, to } = filters;
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<RequestCard> | null>(null);

  useEffect(() => {
    api<CategoryMeta[]>("/meta/categories").then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      setQuery(q.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(id);
  }, [q]);

  const load = useCallback(() => {
    api<Page<RequestCard>>(
      `/requests${qs({ q: query, status, category_id: category, priority, date_from: from, date_to: to, page, view, assignee, sort: view === "triage" ? "priority" : "newest" })}`,
    )
      .then(setData)
      .catch(() => setData({ items: [], total: 0, page: 1, page_size: 20, pages: 1 }));
  }, [query, status, category, priority, from, to, page, view, assignee]);

  useEffect(load, [load]);
  useEffect(() => {
    onFilters?.({
      date_from: from || undefined,
      date_to: to || undefined,
      category_id: category ? Number(category) : undefined,
      priority: priority || undefined,
      status: status || undefined,
    });
  }, [onFilters, from, to, category, priority, status]);
  useRealtimeEvent((e) => {
    if (["status_changed", "request_updated", "request_new", "triage_new"].includes(e.event)) load();
  });

  const applyFilters = (next: typeof DEFAULT_FILTERS) => {
    setFilters(next);
    setPage(1);
  };
  const filtered = Boolean(q || status || category || priority || from || to);
  const clear = () => {
    setQ("");
    setQuery("");
    applyFilters(DEFAULT_FILTERS);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="relative min-w-0 flex-1 sm:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
          <Input type="search" aria-label={t("common.search")} placeholder={t("list.searchPlaceholder")} value={q} onChange={(e) => setQ(e.target.value)} className="min-w-0 pl-9" />
        </div>
        <FilterDialog value={filters} defaults={DEFAULT_FILTERS} onApply={applyFilters}>
          {(draft, update) => (
            <>
              {view !== "triage" && (
                <FilterSelect label={t("list.status")} value={draft.status} onChange={(e) => update({ status: e.target.value })}>
                  <option value="">{t("common.all")}</option>
                  {STATUSES.map((s) => <option key={s} value={s}>{t(`status.${s}`)}</option>)}
                </FilterSelect>
              )}
              <FilterSelect label={t("list.priority")} wide={view === "triage"} value={draft.priority} onChange={(e) => update({ priority: e.target.value })}>
                <option value="">{t("common.all")}</option>
                {["Critical", "High", "Medium", "Low"].map((p) => <option key={p} value={p}>{t(`prio.${p}`)}</option>)}
              </FilterSelect>
              <FilterSelect label={t("list.category")} wide value={draft.category} onChange={(e) => update({ category: e.target.value })}>
                <option value="">{t("common.all")}</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </FilterSelect>
              <FilterDate label={t("list.from")} value={draft.from} max={draft.to || undefined} onChange={(e) => update({ from: e.target.value })} />
              <FilterDate label={t("list.to")} value={draft.to} min={draft.from || undefined} onChange={(e) => update({ to: e.target.value })} />
            </>
          )}
        </FilterDialog>
      </div>
      <div className="flex items-center justify-between text-sm text-muted">
        <span aria-live="polite">{data ? t("list.results", { n: data.total }) : ""}</span>
        {filtered && (
          <button type="button" onClick={clear} className="rounded px-1.5 py-1 font-medium text-primary hover:bg-surface-2">
            {t("common.clear")}
          </button>
        )}
      </div>

      {!data ? (
        <Spinner label={t("common.loading")} />
      ) : data.items.length === 0 ? (
        <Empty>{t("common.none")}</Empty>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
          {data.items.map((r) => (
            <li key={r.id}>
              <Link href={`/requests/${r.id}`} className="block px-4 py-3.5 transition-colors hover:bg-surface-2">
                <div className="flex items-start justify-between gap-3">
                  <p className="min-w-0 break-words font-semibold">{r.subject}</p>
                  <StatusBadge status={r.status} />
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
                  <PriorityBadge priority={r.priority} />
                  <CategoryChip name={r.category?.name} />
                  {staff && <SlaBadge sla={r.sla} />}
                </div>
                <p className="mt-1.5 text-sm text-muted">
                  <span className="tabular-nums">{r.id}</span> · 
                  {fmtDate(r.created_at, lang)} · {r.unit?.name ?? "—"}
                  {staff && ` · ${r.assignee?.name ?? t("common.unassigned")}`}
                  {staff && r.student && ` · ${r.student.name}`}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {data && data.pages > 1 && (
        <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
          <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            {t("common.prev")}
          </Button>
          <span className="text-sm">
            {t("common.page")} {page} {t("common.of")} {data.pages}
          </span>
          <Button size="sm" variant="secondary" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
            {t("common.next")}
          </Button>
        </nav>
      )}
    </div>
  );
}
