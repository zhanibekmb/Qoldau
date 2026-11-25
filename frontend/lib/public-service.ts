"use client";

import { useEffect, useState } from "react";
import { api } from "./api";
import type { Priority } from "./types";

interface PublicService {
  support_email: string | null;
  privacy_url: string | null;
  data_contact: string | null;
  attachments_enabled: boolean;
  max_upload_mb: number;
  offices: { id: number; name: string; email: string; working_hours: string; is_triage: boolean }[];
  sla: { priority: Priority; first_response_hours: number; resolution_hours: number; use_working_hours: boolean }[];
}

export function usePublicService() {
  const [service, setService] = useState<PublicService>();
  useEffect(() => {
    const controller = new AbortController();
    api<PublicService>("/meta/public", { cache: "no-store", signal: controller.signal }).then(setService).catch(() => {});
    return () => controller.abort();
  }, []);
  return service;
}
