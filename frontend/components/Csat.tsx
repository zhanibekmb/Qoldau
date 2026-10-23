"use client";

import clsx from "clsx";
import { Star } from "lucide-react";
import { useState } from "react";
import { api, ApiError, sanitize } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button, Card, FieldError, Textarea } from "./ui";

export function Stars({ value, onPick, size = "h-8 w-8" }: { value: number; onPick?: (n: number) => void; size?: string }) {
  return (
    <div className="flex gap-1" role={onPick ? "radiogroup" : undefined} aria-label="Rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          disabled={!onPick}
          role={onPick ? "radio" : undefined}
          aria-checked={onPick ? value === n : undefined}
          aria-label={`${n} / 5`}
          onClick={() => onPick?.(n)}
          className={clsx("grid min-h-11 min-w-11 place-items-center rounded-lg", onPick && "hover:bg-surface-2")}
        >
          <Star className={clsx(size, n <= value ? "fill-yellow-400 text-yellow-500" : "text-muted")} aria-hidden />
        </button>
      ))}
    </div>
  );
}

/** CSAT survey shown when a request is resolved (US15). */
export function CsatCard({ requestId, onDone }: { requestId: string; onDone: () => void }) {
  const { t } = useI18n();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!rating) return;
    setBusy(true);
    try {
      await api(`/requests/${requestId}/csat`, { method: "POST", json: { rating, comment: sanitize(comment) } });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="border-primary/40 bg-primary-soft/40">
      <form onSubmit={submit} className="space-y-3">
        <h2 className="font-semibold">{t("csat.title")}</h2>
        <Stars value={rating} onPick={setRating} />
        <Textarea rows={2} aria-label={t("csat.comment")} placeholder={t("csat.comment")} value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} />
        <FieldError>{error}</FieldError>
        <Button type="submit" disabled={!rating} loading={busy}>
          {t("csat.submit")}
        </Button>
      </form>
    </Card>
  );
}
