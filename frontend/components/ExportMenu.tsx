"use client";

import { ChevronDown, Download, FileSpreadsheet, FileText } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Button, Toast } from "./ui";

export type ExportFilters = Record<string, string | number | undefined | null>;

/** Export dropdown (US17): sends the filters currently applied on the page. Unit heads and admins only. */
export function ExportMenu({ filters }: { filters: ExportFilters }) {
  const { user } = useAuth();
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ msg: string; tone: "info" | "error" } | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  if (!user || (user.role !== "admin" && user.role !== "unit_head")) return null;

  async function start(kind: "excel" | "pdf") {
    setOpen(false);
    setBusy(true);
    const body = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== "" && v !== undefined && v !== null));
    try {
      await api(`/export/${kind}`, { method: "POST", json: body });
      setToast({ msg: t("rep.started"), tone: "info" });
    } catch (err) {
      setToast({ msg: err instanceof ApiError ? err.message : t("common.error"), tone: "error" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div ref={ref} className="relative">
      <Button variant="secondary" loading={busy} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <Download className="h-4 w-4" aria-hidden /> {t("rep.export")} <ChevronDown className="h-4 w-4" aria-hidden />
      </Button>
      {open && (
        <div role="menu" className="absolute right-0 z-20 mt-1 w-56 rounded-md border border-border bg-surface p-1 shadow-lg">
          <button role="menuitem" className="flex min-h-11 w-full items-center gap-2 rounded px-3 text-left text-sm hover:bg-surface-2" onClick={() => start("excel")}>
            <FileSpreadsheet className="h-4 w-4 text-ok" aria-hidden /> {t("rep.excel")}
          </button>
          <button role="menuitem" className="flex min-h-11 w-full items-center gap-2 rounded px-3 text-left text-sm hover:bg-surface-2" onClick={() => start("pdf")}>
            <FileText className="h-4 w-4 text-critical" aria-hidden /> {t("rep.pdf")}
          </button>
          <Link role="menuitem" href="/reports" className="flex min-h-11 items-center rounded px-3 text-sm text-primary hover:bg-surface-2">
            {t("rep.openReports")}
          </Link>
        </div>
      )}
      {toast && <Toast message={toast.msg} tone={toast.tone} onDone={() => setToast(null)} />}
    </div>
  );
}
