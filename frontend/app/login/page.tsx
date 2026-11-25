"use client";

import { ArrowLeft } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import campus from "@/assets/sdu-campus.jpeg";
import { Logo } from "@/components/Logo";
import { Button, FieldError, Input, Label } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { homeFor, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { usePublicService } from "@/lib/public-service";
import type { Lang, Role } from "@/lib/types";

interface DemoLogin { password: string; accounts: { email: string; role: Role; triage?: boolean }[] }

function LoginForm() {
  const { login, changePassword, user, logout } = useAuth();
  const { t, lang, setLang } = useI18n();
  const service = usePublicService();
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<DemoLogin>();
  const changing = user?.must_change_password;

  useEffect(() => {
    const controller = new AbortController();
    api<DemoLogin>("/auth/demo", { cache: "no-store", signal: controller.signal }).then(setDemo).catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!user || user.must_change_password) return;
    if (next?.startsWith("/")) {
      try {
        const target = new URL(next, window.location.origin);
        if (target.origin === window.location.origin && (target.pathname !== "/requests/new" || user.role === "student")) {
          router.replace(`${target.pathname}${target.search}${target.hash}`);
          return;
        }
      } catch {}
    }
    router.replace(homeFor(user.role));
  }, [user, next, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (changing && newPassword !== confirmation) {
      setError(t("pilot.passwordMismatch"));
      document.getElementById("password-confirm")?.focus();
      return;
    }
    setBusy(true);
    try {
      if (changing) await changePassword(password, newPassword);
      else await login(email.trim(), password);
      setPassword("");
      setNewPassword("");
      setConfirmation("");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? t("pilot.tryLater") :
        changing ? t("pilot.passwordError") : t("auth.invalid"));
      if (changing) {
        await logout();
        setPassword("");
        setNewPassword("");
        setConfirmation("");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="sign-in-title" className="w-full max-w-[26rem] rounded-2xl border border-border bg-surface px-5 py-6 text-text sm:px-8 sm:py-8">
      <div className="text-center">
        <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center">
          <Link href="/" className="inline-flex min-h-11 items-center gap-1.5 justify-self-start rounded-md text-sm font-medium text-muted hover:text-text">
            <ArrowLeft className="size-4 shrink-0" aria-hidden />
            {t("common.back")}
          </Link>
          <Link href="/" aria-label="Qoldau — home" className="inline-flex min-h-11 items-center">
            <Logo />
          </Link>
        </div>
        <h1 id="sign-in-title" className="display-type mt-5 text-[2rem] leading-tight font-semibold tracking-[-0.045em]">{t(changing ? "pilot.changePassword" : "auth.login")}</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted">{t(changing ? "pilot.changeHelp" : "tagline")}</p>
      </div>
      <form key={changing ? "change" : "login"} onSubmit={submit} className="mt-6 space-y-4">
        {changing ? <input type="text" autoComplete="username" name="username" value={user.email} readOnly hidden /> : <div>
          <Label htmlFor="email">{t("auth.email")}</Label>
          <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>}
        <div>
          <Label htmlFor="password">{t(changing ? "pilot.currentPassword" : "auth.password")}</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {changing && <>
          <div>
            <Label htmlFor="password-new">{t("pilot.newPassword")}</Label>
            <Input id="password-new" type="password" autoComplete="new-password" minLength={12} maxLength={72} required
              aria-describedby="password-rules" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            <p id="password-rules" className="mt-1 text-xs text-muted">{t("pilot.passwordRules")}</p>
          </div>
          <div>
            <Label htmlFor="password-confirm">{t("pilot.confirmPassword")}</Label>
            <Input id="password-confirm" type="password" autoComplete="new-password" required
              value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
          </div>
        </>}
        <FieldError>{error}</FieldError>
        <Button type="submit" className="w-full" loading={busy}>
          {t(changing ? "pilot.changePassword" : "auth.login")}
        </Button>
      </form>
      {!changing && <div className="mt-3 text-right text-sm">
        <Link href="/forgot-password" className="font-medium text-primary underline underline-offset-4">
          {t("auth.forgotPassword")}
        </Link>
      </div>}
      {changing ? <Button type="button" variant="ghost" className="mt-2 w-full" disabled={busy}
        onClick={() => { setPassword(""); setNewPassword(""); setConfirmation(""); setError(""); void logout(); }}>
        {t("pilot.signOut")}
      </Button> : <div className="mt-5 border-t border-border pt-4 text-sm">
        <p className="font-medium">{t("pilot.access")}</p>
        <p className="mt-1 text-muted">{t("pilot.accessHelp")}</p>
        {service?.support_email && <a href={`mailto:${service.support_email}`} className="mt-2 inline-block font-medium text-primary underline">{t("pilot.support")}</a>}
      </div>}
      {!changing && demo && <div className="mt-5 border-t border-border pt-4">
        <p className="mb-2 text-sm text-muted">
          {t("auth.demo")} · <span className="font-semibold text-text">{demo.password}</span>
        </p>
        <div className="flex flex-wrap gap-2">
          {demo.accounts.map(({ role, email: mail, triage }) => (
            <Button
              key={mail}
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => {
                setEmail(mail);
                setPassword(demo.password);
              }}
            >
              {t(({ student: "pilot.demoStudent", admin: "pilot.demoAdmin", unit_head: "pilot.demoHead",
                agent: triage ? "pilot.demoTriage" : "pilot.demoAgent" } as const)[role])}
            </Button>
          ))}
        </div>
      </div>}
      <div className="mt-3 flex justify-center gap-1" role="group" aria-label={t("common.language")}>
        {(["kz", "ru", "en"] as Lang[]).map((l) => (
          <Button key={l} type="button" size="sm" variant="ghost" aria-pressed={l === lang} className={l === lang ? "text-text" : "font-normal text-muted"} onClick={() => setLang(l)}>
            {l.toUpperCase()}
          </Button>
        ))}
      </div>
    </section>
  );
}

export default function LoginPage() {
  return (
    <main className="relative isolate grid min-h-svh place-items-center bg-landing-field px-4 py-8 sm:py-10">
      <Image src={campus} alt="" fill preload unoptimized className="-z-20 object-cover object-center" />
      <div aria-hidden className="absolute inset-0 -z-10 dark:bg-black/25" />
      <Suspense>
        <LoginForm />
      </Suspense>
    </main>
  );
}
