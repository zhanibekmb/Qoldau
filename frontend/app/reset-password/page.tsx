"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
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

function ResetPasswordForm() {
  const { t } = useI18n();
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!token) { setError(t("auth.resetInvalid")); return; }
    if (password !== confirmation) { setError(t("auth.resetMismatch")); return; }
    setBusy(true);
    try {
      await api("/auth/password-reset/confirm", {
        method: "POST", json: { token, new_password: password, confirm_password: confirmation },
      });
      setSuccess(true);
      setPassword("");
      setConfirmation("");
    } catch {
      setError(t("auth.resetInvalid"));
    } finally {
      setBusy(false);
    }
  }

  return <main className="grid min-h-svh place-items-center bg-landing-field px-4 py-8">
    <section aria-labelledby="reset-title" className="w-full max-w-[26rem] rounded-2xl border border-border bg-surface px-5 py-6 text-text sm:px-8 sm:py-8">
      <div className="flex items-center justify-between">
        <Link href="/login" className="min-h-11 inline-flex items-center text-sm font-medium text-muted hover:text-text">{t("auth.backToLogin")}</Link>
        <Link href="/" aria-label="Qoldau — home" className="inline-flex min-h-11 items-center"><Logo /></Link>
      </div>
      <h1 id="reset-title" className="display-type mt-5 text-[2rem] leading-tight font-semibold tracking-[-0.045em]">{t("auth.resetTitle")}</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted">{t("auth.resetHelp")}</p>
      {success ? <div className="mt-6 space-y-4"><p role="status" className="rounded-md border border-border bg-surface-2 p-3 text-sm">{t("auth.resetSuccess")}</p>
        <Link href="/login" className="inline-block text-sm font-medium text-primary underline underline-offset-4">{t("auth.backToLogin")}</Link></div> :
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div><Label htmlFor="new-password">{t("pilot.newPassword")}</Label>
            <Input id="new-password" type="password" autoComplete="new-password" minLength={12} maxLength={72} required
              value={password} onChange={(e) => setPassword(e.target.value)} /></div>
          <div><Label htmlFor="confirm-password">{t("auth.confirmPassword")}</Label>
            <Input id="confirm-password" type="password" autoComplete="new-password" minLength={12} maxLength={72} required
              value={confirmation} onChange={(e) => setConfirmation(e.target.value)} /></div>
          <FieldError>{error}</FieldError>
          <Button type="submit" className="w-full" loading={busy}>{t("auth.resetTitle")}</Button>
        </form>}
      <LanguagePicker />
    </section>
  </main>;
}

export default function ResetPasswordPage() {
  return <Suspense><ResetPasswordForm /></Suspense>;
}
