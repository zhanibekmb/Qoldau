"use client";

import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Lock } from "lucide-react";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PriorityBadge } from "@/components/badges";
import { ExportMenu } from "@/components/ExportMenu";
import { Guard } from "@/components/Guard";
import { Card, Input, Select, Spinner } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { CategoryMeta, Lang, Priority, UnitMeta } from "@/lib/types";

interface Dashboard {
  filters: { unit_id: number | null };
  kpis: {
    total: number;
    open: number;
    resolved: number;
    avg_first_response_hours: number | null;
    avg_resolution_hours: number | null;
    sla_compliance: number | null;
    csat_avg: number | null;
    csat_count: number;
    ai_accuracy: number | null;
    overrides: number;
    deflections: number;
    deflection_rate: number | null;
    smart_reply_requests: number;
    smart_reply_usage: number | null;
  };
  over_time: { date: string; created: number; resolved: number }[];
  by_category: { category: string; count: number }[];
  by_unit: { unit: string; new: number; in_progress: number; waiting: number; resolved: number }[];
  priority: { priority: string; count: number }[];
  sla_by_priority: { priority: string; decided: number; compliance: number | null }[];
  top_keywords: { keyword: string; count: number }[];
  leaderboard: { agent_id: number; agent: string; resolved: number; open: number; avg_resolution_hours: number | null; csat: number | null }[];
  ai_by_category: { category: string; classified: number; overridden: number; accuracy: number }[];
}

const RANGES = [
  ["7", "an.range7"],
  ["30", "an.range30"],
  ["90", "an.range90"],
  ["", "an.rangeAll"],
  ["custom", "an.rangeCustom"],
];

// Targets from the SLA policy; only these KPIs have an agreed target.
const FIRST_RESPONSE_TARGET_H = 4;
const SLA_TARGET = 90;
const PRIORITIES: Priority[] = ["Critical", "High", "Medium", "Low"];

// Workload stack: categorical slots in fixed order (validated palette in globals.css).
const STACK = [
  { key: "new", label: "an.new", color: "var(--series-1)" },
  { key: "in_progress", label: "an.inProgress", color: "var(--series-2)" },
  { key: "waiting", label: "an.waiting", color: "var(--series-3)" },
  { key: "resolved", label: "an.resolved", color: "var(--series-4)" },
] as const;

const LINES = [
  { key: "created", label: "an.created", color: "var(--series-1)" },
  { key: "resolved", label: "an.resolved", color: "var(--series-2)" },
] as const;

const locale = (lang: Lang) => (lang === "kz" ? "kk" : lang);
const num = (v: number, lang: Lang, digits = 1) => v.toLocaleString(locale(lang), { maximumFractionDigits: digits });
const shortDate = (d: string, lang: Lang) => new Date(`${d}T00:00:00`).toLocaleDateString(locale(lang), { day: "numeric", month: "short" });

const axis = { stroke: "var(--muted)", fontSize: 12, tickLine: false, axisLine: false } as const;

function Swatch({ color }: { color: string }) {
  return <span aria-hidden className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: color }} />;
}

function Legend({ items }: { items: { label: string; color: string; value?: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          <Swatch color={i.color} />
          <span>{i.label}</span>
          {i.value && <span className="font-semibold">{i.value}</span>}
        </li>
      ))}
    </ul>
  );
}

function Kpi({ label, value, hint, status }: { label: string; value: string; hint?: string; status?: { ok: boolean; text: string } }) {
  return (
    <Card className="flex flex-col p-4">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-1 text-3xl font-bold">{value}</div>
      <div className="mt-auto pt-1 text-sm text-muted">
        {status && (
          <span className={clsx("mr-1.5 inline-flex items-center gap-1 font-semibold", status.ok ? "text-ok" : "text-warn")}>
            {status.ok ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : <AlertTriangle className="h-4 w-4" aria-hidden />}
            {status.text}
          </span>
        )}
        {hint}
      </div>
    </Card>
  );
}

function Panel({ title, sub, aside, children, className }: { title: string; sub?: string; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <Card className={className}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          {sub && <p className="text-sm text-muted">{sub}</p>}
        </div>
        {aside}
      </div>
      {children}
    </Card>
  );
}

/** Same numbers as the chart above it, for screen readers and exact reading. */
function TableView({ label, head, rows }: { label: string; head: string[]; rows: (string | number)[][] }) {
  return (
    <details className="mt-4 text-sm">
      <summary className="inline-flex min-h-11 cursor-pointer items-center font-semibold text-primary">{label}</summary>
      <div className="mt-2 max-h-80 overflow-auto">
        <table className="w-full">
          <thead className="sticky top-0 bg-surface text-left text-muted">
            <tr>
              {head.map((h, i) => (
                <th key={h} className={clsx("py-1.5 font-medium", i > 0 && "text-right")}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={String(r[0])} className="border-t border-border">
                {r.map((c, i) => (
                  <td key={i} className={clsx("py-1.5", i > 0 && "text-right tabular-nums")}>
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

/** Ranked horizontal bars with the label and value written out, so nothing is truncated or hover-only. */
function BarList({ rows, color = "var(--series-1)", max: fixedMax }: { rows: { label: string; value: number; display?: string }[]; color?: string; max?: number }) {
  const max = fixedMax ?? Math.max(1, ...rows.map((r) => r.value));
  return (
    <ul className="space-y-2.5">
      {rows.map((r) => (
        <li key={r.label} className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 text-sm">
          <span className="truncate" title={r.label}>
            {r.label}
          </span>
          <span className="h-2.5 rounded-r bg-surface-2">
            <span className="block h-full rounded-r" style={{ width: `${(r.value / max) * 100}%`, background: color }} />
          </span>
          <span className="w-12 text-right font-semibold tabular-nums">{r.display ?? r.value}</span>
        </li>
      ))}
    </ul>
  );
}

interface TipProps {
  active?: boolean;
  label?: string;
  payload?: { dataKey?: string | number; name?: string; value?: number; color?: string }[];
  fmtLabel: (l: string) => string;
}

function ChartTooltip({ active, label, payload, fmtLabel }: TipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-sm shadow-lg">
      <div className="mb-1 font-semibold">{fmtLabel(String(label))}</div>
      {payload.map((p) => (
        <div key={String(p.dataKey)} className="flex items-center gap-2">
          <Swatch color={p.color ?? "var(--muted)"} />
          <span className="text-muted">{p.name}</span>
          <span className="ml-auto pl-4 font-semibold tabular-nums">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

function AnalyticsView() {
  const { user } = useAuth();
  const { t, lang } = useI18n();
  const isAdmin = user?.role === "admin";
  const [range, setRange] = useState("30");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [unitId, setUnitId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [units, setUnits] = useState<UnitMeta[]>([]);
  const [cats, setCats] = useState<CategoryMeta[]>([]);
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<UnitMeta[]>("/meta/units").then(setUnits).catch(() => {});
    api<CategoryMeta[]>("/meta/categories").then(setCats).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = range === "custom" ? { date_from: from, date_to: to } : { days: range || undefined };
    api<Dashboard>(`/analytics/dashboard${qs({ ...params, unit_id: isAdmin ? unitId : undefined, category_id: categoryId })}`)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [range, from, to, unitId, categoryId, isAdmin]);

  const exportFilters = {
    ...(range === "custom" ? { date_from: from, date_to: to } : { days: range ? Number(range) : undefined }),
    unit_id: isAdmin && unitId ? Number(unitId) : undefined,
    category_id: categoryId ? Number(categoryId) : undefined,
  };
  const lockedUnit = !isAdmin ? units.find((u) => u.id === user?.unit_id)?.name ?? user?.unit_name : null;
  const k = data?.kpis;
  const hours = (v: number | null) => (v === null ? "—" : t("an.hours", { v: num(v, lang) }));
  const pct = (v: number | null) => (v === null ? "—" : `${num(v, lang)}%`);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <h1 className="text-2xl font-bold">{t("nav.analytics")}</h1>
        {/* One filter row scopes every chart on the page */}
        <div className="flex flex-wrap items-center gap-2">
          <Select aria-label={t("an.rangeCustom")} value={range} onChange={(e) => setRange(e.target.value)} className="w-auto">
            {RANGES.map(([v, l]) => (
              <option key={v} value={v}>
                {t(l)}
              </option>
            ))}
          </Select>
          {range === "custom" && (
            <>
              <Input type="date" aria-label={t("list.from")} value={from} onChange={(e) => setFrom(e.target.value)} className="w-auto" />
              <Input type="date" aria-label={t("list.to")} value={to} onChange={(e) => setTo(e.target.value)} className="w-auto" />
            </>
          )}
          {isAdmin ? (
            <Select aria-label={t("an.office")} value={unitId} onChange={(e) => setUnitId(e.target.value)} className="w-auto max-w-[16rem]">
              <option value="">{t("an.allUnits")}</option>
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </Select>
          ) : (
            <span className="inline-flex min-h-11 items-center gap-2 rounded-md bg-surface-2 px-3 text-sm" title={t("an.lockedUnit")}>
              <Lock className="h-4 w-4 text-muted" aria-hidden /> {lockedUnit}
            </span>
          )}
          <Select aria-label={t("an.topic")} value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="w-auto max-w-[16rem]">
            <option value="">{t("an.allCategories")}</option>
            {cats.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <ExportMenu filters={exportFilters} />
        </div>
      </div>

      {!data || !k ? (
        <Spinner label={t("common.loading")} />
      ) : (
        // Hold the previous numbers (dimmed) while a new filter loads; no layout jump.
        <div className={clsx("space-y-6 transition-opacity", loading && "opacity-60")} aria-busy={loading}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label={t("an.total")} value={num(k.total, lang, 0)} hint={t("an.totalHint", { open: k.open, resolved: k.resolved })} />
            <Kpi
              label={t("an.firstResponse")}
              value={hours(k.avg_first_response_hours)}
              status={k.avg_first_response_hours === null ? undefined : { ok: k.avg_first_response_hours < FIRST_RESPONSE_TARGET_H, text: k.avg_first_response_hours < FIRST_RESPONSE_TARGET_H ? t("an.onTarget") : t("an.offTarget") }}
              hint={t("an.target", { v: `< ${t("an.hours", { v: FIRST_RESPONSE_TARGET_H })}` })}
            />
            <Kpi label={t("an.resolution")} value={hours(k.avg_resolution_hours)} />
            <Kpi
              label={t("an.sla")}
              value={pct(k.sla_compliance)}
              status={k.sla_compliance === null ? undefined : { ok: k.sla_compliance >= SLA_TARGET, text: k.sla_compliance >= SLA_TARGET ? t("an.onTarget") : t("an.offTarget") }}
              hint={t("an.target", { v: `≥ ${SLA_TARGET}%` })}
            />
            <Kpi label={t("an.csat")} value={k.csat_avg === null ? "—" : `${num(k.csat_avg, lang, 2)} / 5`} hint={t("an.csatHint", { n: k.csat_count })} />
            <Kpi label={t("an.ai")} value={pct(k.ai_accuracy)} hint={t("an.aiHint", { n: k.overrides })} />
            <Kpi label={t("an.deflection")} value={pct(k.deflection_rate)} hint={t("an.deflectionHint", { n: k.deflections })} />
            <Kpi label={t("an.smartReply")} value={pct(k.smart_reply_usage)} hint={t("an.smartReplyHint", { n: k.smart_reply_requests })} />
          </div>

          <Panel
            title={t("an.overTime")}
            aside={
              <Legend
                items={LINES.map((l) => ({
                  label: t(l.label),
                  color: l.color,
                  value: num(data.over_time.reduce((s, d) => s + d[l.key], 0), lang, 0),
                }))}
              />
            }
          >
            {data.over_time.length === 0 ? (
              <p className="py-10 text-center text-muted">{t("an.noData")}</p>
            ) : (
              <div className="h-72">
                <ResponsiveContainer>
                  <LineChart data={data.over_time} margin={{ left: -16, right: 12, top: 8, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="var(--grid)" />
                    <XAxis dataKey="date" {...axis} minTickGap={32} tickFormatter={(d: string) => shortDate(d, lang)} />
                    <YAxis {...axis} allowDecimals={false} width={40} />
                    <Tooltip content={<ChartTooltip fmtLabel={(d) => shortDate(d, lang)} />} cursor={{ stroke: "var(--muted)", strokeWidth: 1 }} />
                    {LINES.map((l) => (
                      <Line
                        key={l.key}
                        type="monotone"
                        dataKey={l.key}
                        name={t(l.label)}
                        stroke={l.color}
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 5, strokeWidth: 2, stroke: "var(--surface)" }}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
            <TableView
              label={t("an.showTable")}
              head={[t("an.date"), t("an.created"), t("an.resolved")]}
              rows={data.over_time.map((d) => [shortDate(d.date, lang), d.created, d.resolved])}
            />
          </Panel>

          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title={t("an.byCategory")}>
              <BarList rows={[...data.by_category].sort((a, b) => b.count - a.count).map((c) => ({ label: c.category, value: c.count }))} />
            </Panel>

            <Panel title={t("an.byUnit")} aside={<Legend items={STACK.map((s) => ({ label: t(s.label), color: s.color }))} />}>
              <ul className="space-y-2.5">
                {[...data.by_unit]
                  .map((u) => ({ ...u, total: u.new + u.in_progress + u.waiting + u.resolved }))
                  .sort((a, b) => b.total - a.total)
                  .map((u, _, all) => (
                    <li key={u.unit} className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 text-sm">
                      <span className="truncate" title={u.unit}>
                        {u.unit}
                      </span>
                      <span className="flex h-2.5 gap-[2px]" style={{ width: `${(u.total / Math.max(1, all[0].total)) * 100}%` }}>
                        {STACK.map((s) =>
                          u[s.key] > 0 ? (
                            <span
                              key={s.key}
                              className="h-full first:rounded-l-sm last:rounded-r"
                              style={{ flexGrow: u[s.key], background: s.color }}
                              title={`${t(s.label)}: ${u[s.key]}`}
                            />
                          ) : null,
                        )}
                      </span>
                      <span className="w-12 text-right font-semibold tabular-nums">{u.total}</span>
                    </li>
                  ))}
              </ul>
              <TableView
                label={t("an.showTable")}
                head={[t("an.office"), ...STACK.map((s) => t(s.label)), t("an.sum")]}
                rows={data.by_unit.map((u) => [u.unit, u.new, u.in_progress, u.waiting, u.resolved, u.new + u.in_progress + u.waiting + u.resolved])}
              />
            </Panel>

            <Panel title={t("an.byPriority")}>
              {(() => {
                const max = Math.max(1, ...data.priority.map((p) => p.count));
                return (
                  <table className="w-full text-sm">
                    <thead className="text-left text-muted">
                      <tr>
                        <th className="pb-2 font-medium">{t("an.urgency")}</th>
                        <th className="pb-2 font-medium">{t("an.requests")}</th>
                        <th className="whitespace-nowrap pb-2 text-right font-medium">{t("an.slaMet")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {PRIORITIES.map((p) => {
                        const count = data.priority.find((x) => x.priority === p)?.count ?? 0;
                        const sla = data.sla_by_priority.find((x) => x.priority === p)?.compliance ?? null;
                        return (
                          <tr key={p} className="border-t border-border">
                            <td className="py-3 pr-3">
                              <PriorityBadge priority={p} />
                            </td>
                            <td className="w-full py-3 pr-3">
                              <div className="flex items-center gap-3">
                                <span className="h-2.5 flex-1 rounded-r bg-surface-2">
                                  <span className="block h-full rounded-r bg-[var(--series-1)]" style={{ width: `${(count / max) * 100}%` }} />
                                </span>
                                <span className="w-10 text-right font-semibold tabular-nums">{count}</span>
                              </div>
                            </td>
                            <td className="whitespace-nowrap py-3 text-right">
                              {sla === null ? (
                                <span className="text-muted">—</span>
                              ) : (
                                <span className={clsx("inline-flex items-center gap-1 font-semibold tabular-nums", sla >= SLA_TARGET ? "text-ok" : "text-warn")}>
                                  {sla >= SLA_TARGET ? <CheckCircle2 className="h-4 w-4" aria-label={t("an.onTarget")} /> : <AlertTriangle className="h-4 w-4" aria-label={t("an.offTarget")} />}
                                  {num(sla, lang)}%
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                );
              })()}
              <p className="mt-3 text-sm text-muted">{t("an.target", { v: `≥ ${SLA_TARGET}%` })}</p>
            </Panel>

            <Panel title={t("an.aiByCategory")} sub={t("an.aiByCategoryHint")}>
              <BarList
                max={100}
                rows={[...data.ai_by_category]
                  .sort((a, b) => a.accuracy - b.accuracy)
                  .map((c) => ({ label: c.category, value: c.accuracy, display: `${num(c.accuracy, lang, 0)}%` }))}
              />
              <TableView
                label={t("an.showTable")}
                head={[t("an.topic"), t("an.classified"), t("an.overridden"), t("an.accuracy")]}
                rows={data.ai_by_category.map((c) => [c.category, c.classified, c.overridden, `${num(c.accuracy, lang)}%`])}
              />
            </Panel>

            <Panel title={t("an.agents")}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-muted">
                    <tr>
                      <th className="pb-2 font-medium">{t("an.agent")}</th>
                      <th className="pb-2 text-right font-medium">{t("an.resolved")}</th>
                      <th className="pb-2 text-right font-medium">{t("an.open")}</th>
                      <th className="pb-2 text-right font-medium">{t("an.avgRes")}</th>
                      <th className="pb-2 text-right font-medium">{t("an.rating")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.leaderboard.map((a) => (
                      <tr key={a.agent_id} className="border-t border-border">
                        <td className="py-2.5 pr-3">{a.agent}</td>
                        <td className="py-2.5 text-right font-semibold tabular-nums">{a.resolved}</td>
                        <td className="py-2.5 text-right tabular-nums">{a.open}</td>
                        <td className="whitespace-nowrap py-2.5 text-right tabular-nums">{hours(a.avg_resolution_hours)}</td>
                        <td className="py-2.5 text-right tabular-nums">{a.csat === null ? "—" : num(a.csat, lang)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title={t("an.keywords")}>
              <BarList rows={data.top_keywords.map((kw) => ({ label: kw.keyword, value: kw.count }))} />
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <Guard roles={["agent", "unit_head", "admin"]}>
      <AnalyticsView />
    </Guard>
  );
}
