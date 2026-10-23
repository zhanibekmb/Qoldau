"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { Button, Card, FieldError, Input, Label } from "@/components/ui";
import { homeFor, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { Lang } from "@/lib/types";

const DEMO = [
  ["Student", "student@qoldau.edu.kz"],
  ["Agent (IT)", "agent1.it@qoldau.edu.kz"],
  ["Agent (Triage)", "agent1.triage@qoldau.edu.kz"],
  ["Unit head (Library)", "head.library@qoldau.edu.kz"],
  ["Admin", "admin@qoldau.edu.kz"],
];

function LoginForm() {
  const { login, user } = useAuth();
  const { t, lang, setLang } = useI18n();
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) router.replace(next && next.startsWith("/") ? next : homeFor(user.role));
  }, [user, next, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
    } catch {
      setError(t("auth.invalid"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-sm">
        <Link href="/" aria-label="Qoldau — home" className="inline-block">
          <Logo />
        </Link>
        <h1 className="mt-8 text-2xl font-bold">{t("auth.login")}</h1>
        <p className="mb-6 mt-1 text-muted">{t("tagline")}</p>
        <Card className="p-6">
          <form onSubmit={submit} noValidate className="space-y-4">
            <div>
              <Label htmlFor="email">{t("auth.email")}</Label>
              <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="password">{t("auth.password")}</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <FieldError>{error}</FieldError>
            <Button type="submit" className="w-full" loading={busy}>
              {t("auth.login")}
            </Button>
          </form>
          <div className="mt-6 border-t border-border pt-5">
            <p className="mb-3 text-sm text-muted">
              {t("auth.demo")} · <span className="font-semibold text-text">Qoldau123!</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {DEMO.map(([label, mail]) => (
                <Button
                  key={mail}
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setEmail(mail);
                    setPassword("Qoldau123!");
                  }}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>
        </Card>
        <div className="mt-4 flex justify-center gap-1" role="group" aria-label={t("common.language")}>
          {(["kz", "ru", "en"] as Lang[]).map((l) => (
            <Button key={l} size="sm" variant="ghost" aria-pressed={l === lang} className={l === lang ? "text-text" : "font-normal text-muted"} onClick={() => setLang(l)}>
              {l.toUpperCase()}
            </Button>
          ))}
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
