"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, FieldError, Input, Label } from "@/components/ui";
import { Logo } from "@/components/Logo";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Lang } from "@/lib/types";

function LanguagePicker() {
  const { t, lang, setLang } = useI18n();
  return <div className="mt-3 flex justify-center gap-1" role="group" aria-label={t("common.language")}>
    {(["kz", "ru", "en"] as Lang[]).map((value) => (
      <Button key={value} type="button" size="sm" variant="ghost" aria-pressed={value === lang}
        className={value === lang ? "text-text" : "font-normal text-muted"} onClick={() => setLang(value)}>
        {value.toUpperCase()}
      </Button>
    ))}
  </div>;
}

export default function ForgotPasswordPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/auth/password-reset/request", { method: "POST", json: { email: email.trim() } });
      setSent(true);
    } catch {
      setError(t("auth.resetRequestError"));
    } finally {
      setBusy(false);
    }
  }

  return <main className="grid min-h-svh place-items-center bg-landing-field px-4 py-8">
    <section aria-labelledby="forgot-title" className="w-full max-w-[26rem] rounded-2xl border border-border bg-surface px-5 py-6 text-text sm:px-8 sm:py-8">
      <div className="flex items-center justify-between">
        <Link href="/login" className="min-h-11 inline-flex items-center text-sm font-medium text-muted hover:text-text">{t("auth.backToLogin")}</Link>
        <Link href="/" aria-label="Qoldau — home" className="inline-flex min-h-11 items-center"><Logo /></Link>
      </div>
      <h1 id="forgot-title" className="display-type mt-5 text-[2rem] leading-tight font-semibold tracking-[-0.045em]">{t("auth.forgotTitle")}</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">{t("auth.forgotHelp")}</p>
      {sent ? <p role="status" className="mt-6 rounded-md border border-border bg-surface-2 p-3 text-sm">{t("auth.resetRequested")}</p> :
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div><Label htmlFor="reset-email">{t("auth.email")}</Label>
            <Input id="reset-email" type="email" autoComplete="email" required maxLength={160}
              value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <FieldError>{error}</FieldError>
          <Button type="submit" className="w-full" loading={busy}>{t("auth.sendResetLink")}</Button>
        </form>}
      <LanguagePicker />
    </section>
  </main>;
}
