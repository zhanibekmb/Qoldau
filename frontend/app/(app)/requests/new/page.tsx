"use client";

import clsx from "clsx";
import { CheckCircle2, FileText, Paperclip, Sparkles, Trash2, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Guard } from "@/components/Guard";
import { SuggestPanel } from "@/components/SuggestPanel";
import { Button, Card, FieldError, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { api, ApiError, sanitize } from "@/lib/api";
import { fileSize } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { CategoryMeta, RequestDetail } from "@/lib/types";

const SUBJECT_MAX = 150;
const DESC_MIN = 10;
const DESC_MAX = 2000;
const MAX_FILE = 10 * 1024 * 1024;
const ALLOWED = ["pdf", "jpg", "jpeg", "png", "docx"];

interface Preview {
  category: string;
  confidence: number;
  needs_review: boolean;
}

function NewRequestForm() {
  const { t } = useI18n();
  const [categories, setCategories] = useState<CategoryMeta[]>([]);
  const [category, setCategory] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState("");
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [created, setCreated] = useState<RequestDetail | null>(null);
  const [dragOver, setDragOver] = useState(false);
  // One suggestion session per form fill: what was shown is saved with the request (US20).
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [deflected, setDeflected] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api<CategoryMeta[]>("/meta/categories").then(setCategories).catch(() => {});
  }, []);

  // Live AI category preview while typing (debounced).
  useEffect(() => {
    const text = description.trim();
    if (text.length < 15) {
      setPreview(null);
      return;
    }
    const id = setTimeout(() => {
      api<Preview>("/ai/classify", { method: "POST", json: { subject, description: text } })
        .then(setPreview)
        .catch(() => setPreview(null));
    }, 600);
    return () => clearTimeout(id);
  }, [subject, description]);

  const errors = useMemo(() => {
    const e: Record<string, string> = {};
    if (!category) e.category = t("form.required");
    const s = subject.trim();
    if (!s) e.subject = t("form.required");
    else if (s.length < 3) e.subject = t("form.tooShort", { n: 3 });
    else if (s.length > SUBJECT_MAX) e.subject = t("form.tooLong", { n: SUBJECT_MAX });
    const d = description.trim();
    if (!d) e.description = t("form.required");
    else if (d.length < DESC_MIN) e.description = t("form.tooShort", { n: DESC_MIN });
    else if (description.length > DESC_MAX) e.description = t("form.tooLong", { n: DESC_MAX });
    return e;
  }, [category, subject, description, t]);

  const overLimit = description.length > DESC_MAX || subject.length > SUBJECT_MAX;
  const show = (f: string) => (tried || touched[f]) && errors[f];

  function addFiles(list: FileList | null) {
    if (!list) return;
    setFileError("");
    const next = [...files];
    for (const f of Array.from(list)) {
      const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
      if (!ALLOWED.includes(ext)) {
        setFileError(`${f.name}: ${t("form.fileType")}`);
        continue;
      }
      if (f.size > MAX_FILE) {
        setFileError(`${f.name}: ${t("form.fileSize")}`);
        continue;
      }
      if (!next.some((x) => x.name === f.name && x.size === f.size)) next.push(f);
    }
    setFiles(next.slice(0, 5));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setTried(true);
    setServerError("");
    if (Object.keys(errors).length) {
      const first = Object.keys(errors)[0];
      document.getElementById(first)?.focus();
      return;
    }
    setBusy(true);
    try {
      const req = await api<RequestDetail>("/requests", {
        method: "POST",
        json: {
          subject: sanitize(subject.trim()),
          description: sanitize(description.trim()),
          category_id: category === "auto" ? null : Number(category),
          suggestion_session: sessionId,
        },
      });
      setCreated(req);
      if (files.length) {
        const ids: number[] = [];
        for (const f of files) {
          const fd = new FormData();
          fd.append("file", f);
          try {
            const a = await api<{ id: number }>(`/requests/${req.id}/attachments`, { method: "POST", body: fd });
            ids.push(a.id);
          } catch {}
        }
        if (ids.length) await api(`/requests/${req.id}/messages`, { method: "POST", json: { body: "", attachment_ids: ids } });
      }
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setCreated(null);
    setCategory("");
    setSubject("");
    setDescription("");
    setFiles([]);
    setTried(false);
    setTouched({});
    setPreview(null);
    setDeflected(false);
    setSessionId(crypto.randomUUID());
  }

  if (deflected)
    return (
      <div className="mx-auto max-w-2xl">
        <Card className="p-6 text-center" role="status">
          <CheckCircle2 className="success-pop mx-auto h-14 w-14 text-ok" aria-hidden />
          <h1 className="mt-3 text-xl font-bold">{t("sug.doneTitle")}</h1>
          <p className="mt-2 text-muted">{t("sug.doneText")}</p>
          <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-center">
            <Link href="/dashboard" className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-fg hover:bg-primary/90">
              {t("sug.backHome")}
            </Link>
            <Button variant="secondary" onClick={reset}>
              {t("form.another")}
            </Button>
          </div>
        </Card>
      </div>
    );

  const counterColor =
    description.length > DESC_MAX ? "text-critical font-semibold" : description.length > DESC_MAX * 0.9 ? "text-warn" : "text-muted";

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">{t("form.title")}</h1>
      <p className="mb-6 mt-1 text-muted">{t("form.intro")}</p>
      <Card className="p-5 sm:p-6">
        <form onSubmit={submit} noValidate className="space-y-5">
          <div>
            <Label htmlFor="category">
              {t("form.category")} <span aria-hidden className="text-critical">*</span>
            </Label>
            <Select
              id="category"
              value={category}
              invalid={!!show("category")}
              aria-describedby="category-err"
              aria-required
              onChange={(e) => setCategory(e.target.value)}
              onBlur={() => setTouched((x) => ({ ...x, category: true }))}
            >
              <option value="">—</option>
              <option value="auto">{t("form.categoryNotSure")}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
            <FieldError id="category-err">{show("category")}</FieldError>
          </div>

          <div>
            <Label htmlFor="subject">
              {t("form.subject")} <span aria-hidden className="text-critical">*</span>
            </Label>
            <Input
              id="subject"
              value={subject}
              maxLength={SUBJECT_MAX + 50}
              invalid={!!show("subject")}
              aria-describedby="subject-err"
              aria-required
              onChange={(e) => setSubject(e.target.value)}
              onBlur={() => setTouched((x) => ({ ...x, subject: true }))}
            />
            <FieldError id="subject-err">{show("subject")}</FieldError>
          </div>

          <div>
            <Label htmlFor="description">
              {t("form.description")} <span aria-hidden className="text-critical">*</span>
            </Label>
            <Textarea
              id="description"
              rows={6}
              value={description}
              invalid={!!show("description") || description.length > DESC_MAX}
              aria-describedby="description-hint description-counter description-err"
              aria-required
              onChange={(e) => setDescription(e.target.value)}
              onBlur={() => setTouched((x) => ({ ...x, description: true }))}
            />
            <div className="mt-1 flex items-start justify-between gap-3 text-sm">
              <span id="description-hint" className="text-muted">
                {t("form.descriptionHint")}
              </span>
              <span id="description-counter" aria-live="polite" className={clsx("shrink-0 tabular-nums", counterColor)}>
                {description.length}/{DESC_MAX}
              </span>
            </div>
            <FieldError id="description-err">{show("description")}</FieldError>
            {preview && (
              <div className="mt-3 flex items-center gap-2 rounded-md bg-primary-soft px-3 py-2 text-sm text-primary" aria-live="polite">
                <Sparkles className="h-4 w-4 shrink-0" aria-hidden />
                {preview.needs_review ? (
                  <span>{t("form.aiUnsure")}</span>
                ) : (
                  <span>
                    {t("form.aiPreview")}: <strong>{preview.category}</strong> ({Math.round(preview.confidence * 100)}%)
                  </span>
                )}
              </div>
            )}
          </div>

          <SuggestPanel subject={subject} description={description} sessionId={sessionId} onDeflect={() => setDeflected(true)} />

          <div>
            <span className="mb-1 block text-sm font-medium">{t("form.attachments")}</span>
            <input
              ref={fileInput}
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.docx"
              className="sr-only"
              id="files"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = "";
              }}
            />
            {/* Desktop: drag & drop zone (fixed height, never blocks scrolling) */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                addFiles(e.dataTransfer.files);
              }}
              className={clsx(
                "hidden h-28 flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed text-sm md:flex",
                dragOver ? "border-primary bg-primary-soft" : "border-border",
              )}
            >
              <UploadCloud className="h-6 w-6 text-muted" aria-hidden />
              <span>
                {t("form.dropHere")}{" "}
                <button type="button" className="font-semibold text-primary underline" onClick={() => fileInput.current?.click()}>
                  {t("form.browse")}
                </button>
              </span>
              <span className="text-xs text-muted">{t("form.fileRules")}</span>
            </div>
            {/* Mobile: wide touch-friendly button (US4) */}
            <div className="md:hidden">
              <Button type="button" variant="secondary" className="h-12 w-full" onClick={() => fileInput.current?.click()}>
                <Paperclip className="h-5 w-5" aria-hidden />
                {t("form.chooseFile")}
              </Button>
              <p className="mt-1 text-xs text-muted">{t("form.fileRules")}</p>
            </div>
            <FieldError>{fileError}</FieldError>
            {files.length > 0 && (
              <ul className="mt-2 space-y-1">
                {files.map((f) => (
                  <li key={f.name + f.size} className="flex items-center gap-2 rounded-md bg-surface-2 px-3 py-1 text-sm">
                    <FileText className="h-4 w-4 shrink-0 text-muted" aria-hidden />
                    <span className="min-w-0 flex-1 truncate">{f.name}</span>
                    <span className="text-muted">{fileSize(f.size)}</span>
                    <button
                      type="button"
                      aria-label={`Remove ${f.name}`}
                      className="grid h-11 w-11 place-items-center rounded-md hover:bg-surface"
                      onClick={() => setFiles(files.filter((x) => x !== f))}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <FieldError>{serverError}</FieldError>
          <Button type="submit" className="w-full sm:w-auto" loading={busy} disabled={overLimit}>
            {busy ? t("form.submitting") : t("form.submit")}
          </Button>
        </form>
      </Card>

      <Modal open={!!created} onClose={reset} title={t("form.success")}>
        {created && (
          <div className="text-center">
            <svg viewBox="0 0 52 52" className="success-pop mx-auto h-20 w-20" aria-hidden>
              <circle cx="26" cy="26" r="24" fill="var(--ok)" />
              <path className="success-check" d="M15 27l7 7 15-15" fill="none" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="mt-4 text-sm text-muted">{t("form.successId")}</p>
            <p className="text-2xl font-bold tabular-nums">{created.id}</p>
            {created.category && (
              <p className="mt-2 text-sm">
                {created.category.name} → {created.unit?.name}
              </p>
            )}
            <p className="mt-3 text-sm text-muted">{t("form.successText")}</p>
            <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-center">
              <Link href={`/requests/${created.id}`} className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-fg hover:bg-primary/90">
                {t("form.view")}
              </Link>
              <Button variant="secondary" onClick={reset}>
                {t("form.another")}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default function NewRequestPage() {
  return (
    <Guard roles={["student"]}>
      <NewRequestForm />
    </Guard>
  );
}
