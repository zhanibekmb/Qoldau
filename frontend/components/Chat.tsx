"use client";

import clsx from "clsx";
import { Check, CheckCheck, FileText, Lock, Paperclip, RotateCw, Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, fileUrl, sanitize } from "@/lib/api";
import { fileSize, fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { type RtEvent, useRequestSocket } from "@/lib/realtime";
import type { Message, User } from "@/lib/types";
import { Button, FieldError } from "./ui";

interface Pending {
  key: string;
  body: string;
  internal: boolean;
  files: File[];
  state: "sending" | "failed";
}

/** Real-time thread inside a request (US15): typing indicator, read receipts, attachments, retry. */
export function Chat({
  requestId,
  viewer,
  closed,
  onEvent,
  insert,
  onSent,
}: {
  requestId: string;
  viewer: User;
  closed: boolean;
  onEvent?: (e: RtEvent) => void;
  /** Text placed in the reply box by a smart-reply "Insert" (US19); a new key re-inserts. */
  insert?: { text: string; key: number };
  onSent?: (body: string, internal: boolean) => void;
}) {
  const { t, lang } = useI18n();
  const staff = viewer.role !== "student";
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [text, setText] = useState("");
  const [internal, setInternal] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [typing, setTyping] = useState<string | null>(null);
  const [error, setError] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const typingTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const lastTypingSent = useRef(0);

  const load = useCallback(() => {
    api<Message[]>(`/requests/${requestId}/messages`).then(setMessages).catch(() => {});
  }, [requestId]);

  useEffect(load, [load]);

  const sendRef = useRef<(p: Record<string, unknown>) => void>(() => {});
  const send = useRequestSocket(requestId, (e) => {
    if (e.event === "message") {
      load();
      if (Number(e.author_id) !== viewer.id && document.visibilityState === "visible") sendRef.current({ type: "read" });
    } else if (e.event === "typing") {
      setTyping(e.is_typing ? String(e.name) : null);
      clearTimeout(typingTimer.current);
      typingTimer.current = setTimeout(() => setTyping(null), 4000);
    } else if (e.event === "read") {
      const ids = new Set((e.message_ids as number[]) ?? []);
      setMessages((ms) => ms.map((m) => (ids.has(m.id) ? { ...m, read_at: String(e.at) } : m)));
    } else if (e.event === "socket_open") {
      load();
    }
    onEvent?.(e);
  });

  useEffect(() => {
    sendRef.current = send;
  }, [send]);

  useEffect(() => {
    if (!insert) return;
    setText(insert.text);
    setInternal(false);
    inputRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    inputRef.current?.focus({ preventScroll: true });
  }, [insert]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages.length, pending.length]);

  async function deliver(p: Pending) {
    setPending((ps) => ps.map((x) => (x.key === p.key ? { ...x, state: "sending" } : x)));
    try {
      const ids: number[] = [];
      for (const f of p.files) {
        const fd = new FormData();
        fd.append("file", f);
        const a = await api<{ id: number }>(`/requests/${requestId}/attachments`, { method: "POST", body: fd });
        ids.push(a.id);
      }
      await api(`/requests/${requestId}/messages`, {
        method: "POST",
        json: { body: sanitize(p.body), is_internal: p.internal, attachment_ids: ids },
      });
      setPending((ps) => ps.filter((x) => x.key !== p.key));
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status < 500 && err.status !== 0) setError(err.message);
      setPending((ps) => ps.map((x) => (x.key === p.key ? { ...x, state: "failed" } : x)));
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!text.trim() && !files.length) return;
    const p: Pending = { key: crypto.randomUUID(), body: text.trim(), internal: staff && internal, files, state: "sending" };
    setPending((ps) => [...ps, p]);
    onSent?.(p.body, p.internal);
    setText("");
    setFiles([]);
    send({ type: "typing", is_typing: false });
    deliver(p);
  }

  function onType(v: string) {
    setText(v);
    const now = Date.now();
    if (now - lastTypingSent.current > 2000) {
      lastTypingSent.current = now;
      send({ type: "typing", is_typing: true });
    }
  }

  return (
    <div className="flex flex-col">
      <div ref={listRef} className="max-h-[28rem] min-h-40 space-y-3 overflow-y-auto pr-1" aria-live="polite">
        {messages.length === 0 && pending.length === 0 && <p className="py-6 text-center text-sm text-muted">{t("common.none")}</p>}
        {messages.map((m) => {
          const mine = m.author.id === viewer.id;
          return (
            <div key={m.id} className={clsx("flex", mine ? "justify-end" : "justify-start")}>
              <div
                className={clsx(
                  "max-w-[85%] rounded-lg px-3 py-2 text-[15px]",
                  m.is_internal ? "bg-yellow-400/20" : mine ? "bg-primary text-primary-fg" : "bg-surface-2",
                )}
              >
                <div className={clsx("mb-0.5 flex items-center gap-1 text-xs font-semibold", mine && !m.is_internal ? "opacity-80" : "text-muted")}>
                  {m.is_internal && <Lock className="h-3 w-3 text-yellow-600" aria-label={t("chat.internal")} />}
                  {m.author.name}
                </div>
                {m.body && <p className="whitespace-pre-wrap break-words">{m.body}</p>}
                {m.attachments.map((a) => (
                  <a
                    key={a.id}
                    href={fileUrl(a.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={clsx("mt-1 flex items-center gap-2 rounded-md px-2 py-1 underline", mine && !m.is_internal ? "bg-white/15" : "bg-surface")}
                  >
                    <FileText className="h-4 w-4 shrink-0" aria-hidden />
                    <span className="truncate">{a.filename}</span>
                    <span className="shrink-0 text-xs opacity-75">{fileSize(a.size)}</span>
                  </a>
                ))}
                <div className={clsx("mt-1 flex items-center justify-end gap-1 text-[11px]", mine && !m.is_internal ? "opacity-75" : "text-muted")}>
                  {fmtDate(m.created_at, lang)}
                  {mine && !m.is_internal &&
                    (m.read_at ? (
                      <CheckCheck className="h-3.5 w-3.5" aria-label={t("chat.read")} />
                    ) : (
                      <Check className="h-3.5 w-3.5" aria-label={t("chat.sent")} />
                    ))}
                </div>
              </div>
            </div>
          );
        })}
        {pending.map((p) => (
          <div key={p.key} className="flex justify-end">
            <div className={clsx("max-w-[85%] rounded-lg px-3 py-2 text-[15px]", p.state === "failed" ? "bg-critical/10" : "bg-primary/60 text-primary-fg")}>
              <p className="whitespace-pre-wrap break-words">{p.body || p.files.map((f) => f.name).join(", ")}</p>
              {p.state === "failed" ? (
                <button className="mt-1 flex min-h-11 items-center gap-1 text-xs font-semibold text-critical" onClick={() => deliver(p)}>
                  <RotateCw className="h-3.5 w-3.5" /> {t("chat.failed")} · {t("common.retry")}
                </button>
              ) : (
                <div className="mt-1 text-right text-[11px] opacity-75">…</div>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="h-5 text-xs text-muted" aria-live="polite">
        {typing && t("chat.typing", { name: typing })}
      </div>

      {closed ? (
        <p className="rounded-md bg-surface-2 p-3 text-center text-sm text-muted">{t("chat.closed")}</p>
      ) : (
        <form onSubmit={submit} className="space-y-2">
          {staff && (
            <label className="flex min-h-11 items-center gap-2 text-sm">
              <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} className="h-5 w-5" />
              <Lock className="h-4 w-4 text-yellow-600" aria-hidden /> {t("chat.internal")}
            </label>
          )}
          {files.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {files.map((f) => (
                <span key={f.name} className="flex items-center gap-1 rounded-md bg-surface-2 py-1 pl-3 pr-1 text-xs">
                  {f.name}
                  <button type="button" aria-label={`Remove ${f.name}`} className="grid h-8 w-8 place-items-center" onClick={() => setFiles(files.filter((x) => x !== f))}>
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.docx"
              className="sr-only"
              onChange={(e) => {
                const list = Array.from(e.target.files ?? []).filter((f) => f.size <= 10 * 1024 * 1024);
                setFiles((x) => [...x, ...list].slice(0, 5));
                e.target.value = "";
              }}
            />
            <Button type="button" variant="secondary" aria-label={t("chat.attach")} onClick={() => fileRef.current?.click()}>
              <Paperclip className="h-5 w-5" />
            </Button>
            <textarea
              ref={inputRef}
              value={text}
              onChange={(e) => onType(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(e);
                }
              }}
              rows={Math.min(8, Math.max(1, text.split("\n").length))}
              maxLength={2000}
              aria-label={t("chat.placeholder")}
              placeholder={internal ? t("chat.internalPlaceholder") : t("chat.placeholder")}
              className={clsx(
                "min-h-11 flex-1 resize-none rounded-md border bg-surface px-3 py-2.5 text-[15px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25",
                internal ? "border-yellow-500" : "border-border",
              )}
            />
            <Button type="submit" aria-label={t("chat.send")} disabled={!text.trim() && !files.length}>
              <Send className="h-5 w-5" />
            </Button>
          </div>
          <FieldError>{error}</FieldError>
        </form>
      )}
    </div>
  );
}
