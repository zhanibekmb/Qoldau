"use client";

import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Guard } from "@/components/Guard";
import { Badge, Card, Empty, Spinner } from "@/components/ui";
import { api, fileUrl } from "@/lib/api";
import { fileSize, fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRealtimeEvent } from "@/lib/realtime";
import type { CategoryMeta, ReportJob, UnitMeta } from "@/lib/types";

const STATUS_CLS: Record<ReportJob["status"], string> = {
  queued: "bg-surface-2 text-muted",
  running: "bg-primary-soft text-primary",
  done: "bg-ok/12 text-ok",
  failed: "bg-critical/12 text-critical",
};

/** "My exports" (US17): status, filters summary and signed download links (valid 24 h). */
function ReportsView() {
  const { t, lang } = useI18n();
  const [jobs, setJobs] = useState<ReportJob[] | null>(null);
  const [units, setUnits] = useState<UnitMeta[]>([]);
  const [cats, setCats] = useState<CategoryMeta[]>([]);

  const load = useCallback(() => {
    api<ReportJob[]>("/export/jobs").then(setJobs).catch(() => setJobs([]));
  }, []);

  useEffect(() => {
    load();
    api<UnitMeta[]>("/meta/units").then(setUnits).catch(() => {});
    api<CategoryMeta[]>("/meta/categories").then(setCats).catch(() => {});
  }, [load]);

  // The bell notification arrives over the WebSocket when a job finishes; poll as a fallback while jobs run.
  useRealtimeEvent((e) => {
    if (e.event === "notification") load();
  });
  const busy = jobs?.some((j) => j.status === "queued" || j.status === "running");
  useEffect(() => {
    if (!busy) return;
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [busy, load]);

  const describe = (f: ReportJob["filters"]) => {
    const parts: string[] = [];
    if (f.date_from || f.date_to) parts.push(`${f.date_from ?? "…"} – ${f.date_to ?? "…"}`);
    else parts.push(f.days ? t("rep.lastDays", { n: f.days }) : t("rep.allTime"));
    if (f.unit_id) parts.push(units.find((u) => u.id === Number(f.unit_id))?.name ?? `#${f.unit_id}`);
    if (f.category_id) parts.push(cats.find((c) => c.id === Number(f.category_id))?.name ?? `#${f.category_id}`);
    if (f.priority) parts.push(String(f.priority));
    if (f.status) parts.push(String(f.status));
    return parts.join(" · ");
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{t("nav.reports")}</h1>
        <p className="mt-1 text-muted">{t("rep.intro")}</p>
      </div>
      {!jobs ? (
        <Spinner label={t("common.loading")} />
      ) : jobs.length === 0 ? (
        <Empty>{t("rep.empty")}</Empty>
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs text-muted">
              <tr>
                <th className="p-3 font-medium">{t("rep.type")}</th>
                <th className="p-3 font-medium">{t("rep.filters")}</th>
                <th className="p-3 font-medium">{t("rep.created")}</th>
                <th className="p-3 font-medium">{t("kb.status")}</th>
                <th className="p-3 text-right font-medium">{t("rep.rows")}</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-t border-border align-middle">
                  <td className="whitespace-nowrap p-3">
                    <span className="inline-flex items-center gap-2 font-medium">
                      {j.type === "excel" ? <FileSpreadsheet className="h-4 w-4 text-ok" aria-hidden /> : <FileText className="h-4 w-4 text-critical" aria-hidden />}
                      {j.type === "excel" ? "Excel" : "PDF"}
                    </span>
                  </td>
                  <td className="p-3">{describe(j.filters)}</td>
                  <td className="whitespace-nowrap p-3 text-muted">{fmtDate(j.created_at, lang)}</td>
                  <td className="p-3">
                    <Badge className={STATUS_CLS[j.status]}>
                      {(j.status === "queued" || j.status === "running") && <Loader2 className="h-3 w-3 animate-spin" aria-hidden />}
                      {t(`rep.st.${j.status}`)}
                    </Badge>
                    {j.error && <div className="mt-1 max-w-xs text-xs text-critical">{j.error}</div>}
                  </td>
                  <td className="p-3 text-right tabular-nums">{j.row_count ?? "—"}</td>
                  <td className="whitespace-nowrap p-2 text-right">
                    {j.download_url && (
                      <a
                        href={fileUrl(j.download_url)}
                        className="inline-flex min-h-11 items-center gap-2 rounded-md bg-primary px-3 text-sm font-semibold text-primary-fg hover:bg-primary/90"
                      >
                        <Download className="h-4 w-4" aria-hidden /> {t("rep.download")}
                        {j.file_size ? <span className="font-normal opacity-80">{fileSize(j.file_size)}</span> : null}
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Guard roles={["unit_head", "admin"]}>
      <ReportsView />
    </Guard>
  );
}
