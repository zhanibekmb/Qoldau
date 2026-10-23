"use client";

import { useState } from "react";
import { ExportMenu, type ExportFilters } from "@/components/ExportMenu";
import { Guard } from "@/components/Guard";
import { RequestList } from "@/components/RequestList";
import { Button } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function UnitRequestsPage() {
  const { t } = useI18n();
  const [tab, setTab] = useState<"all" | "mine" | "escalated">("all");
  const [filters, setFilters] = useState<ExportFilters>({});
  return (
    <Guard roles={["agent", "unit_head", "admin"]}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("nav.queue")}</h1>
        <ExportMenu filters={filters} />
      </div>
      <div className="mb-3 flex gap-2">
        {(["all", "mine", "escalated"] as const).map((k) => (
          <Button key={k} size="sm" variant={tab === k ? "primary" : "secondary"} onClick={() => setTab(k)}>
            {k === "all" ? t("common.all") : k === "mine" ? t("board.mine") : "Escalated"}
          </Button>
        ))}
      </div>
      <RequestList key={tab} staff view={tab === "escalated" ? "escalated" : "all"} assignee={tab === "mine" ? "me" : undefined} onFilters={setFilters} />
    </Guard>
  );
}
