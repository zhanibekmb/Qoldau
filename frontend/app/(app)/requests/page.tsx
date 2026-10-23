"use client";

import { Guard } from "@/components/Guard";
import { RequestList } from "@/components/RequestList";
import { useI18n } from "@/lib/i18n";

export default function MyRequestsPage() {
  const { t } = useI18n();
  return (
    <Guard roles={["student"]}>
      <h1 className="mb-4 text-2xl font-bold">{t("list.title")}</h1>
      <RequestList />
    </Guard>
  );
}
