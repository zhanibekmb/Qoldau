import type { Lang } from "./types";

const LOCALE: Record<Lang, string> = { en: "en-GB", ru: "ru-RU", kz: "kk-KZ" };

export function fmtDate(iso: string | null | undefined, lang: Lang = "en", withTime = true): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(LOCALE[lang], {
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

export function fmtDuration(seconds: number): string {
  const s = Math.abs(seconds);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "now";
  return fmtDuration(diff);
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
