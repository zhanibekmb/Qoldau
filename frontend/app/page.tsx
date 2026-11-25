"use client";

import { ChevronDown, LayoutDashboard, Moon, Sun } from "lucide-react";
import Link from "next/link";
import { PriorityBadge } from "@/components/badges";
import { RouteDemo } from "@/components/landing/RouteDemo";
import { Logo } from "@/components/Logo";
import { homeFor, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { LANDING } from "@/lib/landing-copy";
import { usePublicService } from "@/lib/public-service";
import { useTheme } from "@/lib/theme";
import type { Lang } from "@/lib/types";

const wrap = "mx-auto max-w-6xl px-4 sm:px-6";
const primaryBtn =
  "inline-flex min-h-12 items-center justify-center rounded-md bg-primary px-6 font-semibold text-primary-fg transition-colors hover:bg-primary/90";

function LangToggle() {
  const { lang, setLang, t } = useI18n();
  const languages: Lang[] = ["kz", "ru", "en"];
  return (
    <>
      <div role="group" aria-label={t("common.language")} className="hidden sm:flex">
        {languages.map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setLang(l)}
            aria-pressed={lang === l}
            className={`min-h-11 min-w-11 rounded-md px-1.5 text-sm transition-colors ${
              lang === l ? "font-bold text-text" : "text-muted hover:bg-surface-2 hover:text-text"
            }`}
          >
            {l.toUpperCase()}
          </button>
        ))}
      </div>
      <select
        aria-label={t("common.language")}
        value={lang}
        onChange={(e) => setLang(e.target.value as Lang)}
        className="h-11 w-12 rounded-md bg-surface px-1 text-sm font-semibold sm:hidden"
      >
        {languages.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
      </select>
    </>
  );
}

function SectionHead({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="max-w-2xl">
      <h2 className="display-type text-3xl font-semibold tracking-tight">{title}</h2>
      {sub && <p className="mt-3 text-lg text-muted">{sub}</p>}
    </div>
  );
}

export default function Landing() {
  const { lang, t } = useI18n();
  const { user } = useAuth();
  const { theme, toggle } = useTheme();
  const service = usePublicService();
  const c = LANDING[lang];
  const number = new Intl.NumberFormat(lang === "kz" ? "kk" : lang);
  const hours = (value: number) => `${number.format(value)} ${c.sla.hourShort}`;
  const faq = [{ q: t("pilot.access"), a: t("pilot.accessHelp") }, ...c.faq.items];
  if (service) {
    faq.push({ q: t("pilot.filesQuestion"), a: service.attachments_enabled ?
      t("pilot.fileRules", { n: service.max_upload_mb }) : t("pilot.filesDisabled") });
  }

  const submitHref = user ? (user.role === "student" ? "/requests/new" : homeFor(user.role)) : "/login?next=/requests/new";
  const portalHref = user ? homeFor(user.role) : "/login";

  return (
    <div className="min-h-screen bg-surface">
      <a href="#main" className="sr-only z-50 rounded-md bg-surface px-4 py-3 font-semibold focus:not-sr-only focus:fixed focus:left-4 focus:top-4">
        {c.nav.skip}
      </a>

      <header className="border-b border-border">
        <div className={`${wrap} flex h-16 items-center gap-2 sm:gap-6`}>
          <Link href="/" aria-label="Qoldau — SDU University" className="flex shrink-0">
            <span className="sm:hidden"><Logo compact /></span>
            <span className="hidden sm:block"><Logo /></span>
          </Link>
          <nav aria-label="Sections" className="hidden items-center gap-1 text-[15px] lg:flex">
            {[
              ["#how", c.nav.how],
              ["#offices", c.nav.offices],
              ["#sla", c.nav.sla],
              ["#faq", c.nav.faq],
            ].map(([href, label]) => (
              <a key={href} href={href} className="rounded-md px-3 py-2 text-muted hover:bg-surface-2 hover:text-text">
                {label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <LangToggle />
            <button type="button" onClick={toggle} aria-label={t("common.theme")} className="grid h-11 w-11 shrink-0 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text">
              {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <Link
              href={portalHref}
              aria-label={user ? c.nav.openPortal : c.nav.signIn}
              className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-md bg-surface-2 px-2.5 text-sm font-semibold hover:bg-border sm:px-4"
            >
              {user ? (
                <>
                  <LayoutDashboard className="size-4 sm:hidden" aria-hidden />
                  <span className="hidden sm:inline">{c.nav.openPortal}</span>
                </>
              ) : c.nav.signIn}
            </Link>
          </div>
        </div>
      </header>

      <main id="main">
        <section className="bg-landing-field">
          <div className={`${wrap} grid items-center gap-7 py-10 sm:gap-9 sm:py-14 md:grid-cols-2 lg:gap-12 lg:py-18`}>
            <div className="min-w-0">
              <h1 className="display-type text-[clamp(1.625rem,7.6vw,2.75rem)] leading-[1.06] font-semibold tracking-[-0.04em] md:text-[clamp(2rem,3.5vw,3.125rem)]">
                <span className="block">{c.hero.title1}</span>{" "}
                <span className="block">{c.hero.title2}</span>
              </h1>
              <p className="mt-4 max-w-lg text-base leading-relaxed text-muted lg:text-lg">{c.hero.sub}</p>
              <Link
                href={submitHref}
                className={`${primaryBtn} mt-6`}
              >
                {user && user.role !== "student" ? c.nav.openPortal : c.hero.ctaStudent}
              </Link>
            </div>
            <RouteDemo copy={c.demo} offices={c.offices.units} lang={lang} />
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="scroll-mt-4 bg-bg">
          <div className={`${wrap} py-20`}>
            <SectionHead title={c.how.title} sub={c.how.sub} />
            <ol className="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8">
              {c.how.steps.map((s, i) => (
                <li key={s.title}>
                  <span className="text-3xl font-bold tabular-nums text-primary" aria-hidden>
                    {i + 1}
                  </span>
                  <h3 className="mt-3 text-lg font-semibold">{s.title}</h3>
                  <p className="mt-2 leading-relaxed text-muted">{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Offices */}
        <section id="offices" className={`${wrap} scroll-mt-4 py-20`}>
          <SectionHead title={c.offices.title} sub={c.offices.sub} />
          {service?.offices.length ? <dl className="mt-8 grid gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
            {service.offices.map((u) => (
              <div key={u.id}>
                <dt className="font-semibold">{u.name}</dt>
                <dd className="mt-1 space-y-0.5 break-words text-sm text-muted">
                  {u.is_triage && <p>{t("nav.triage")}</p>}
                  {u.working_hours && <p>{u.working_hours}</p>}
                  {u.email && <a className="text-primary underline" href={`mailto:${u.email}`}>{u.email}</a>}
                </dd>
              </div>
            ))}
          </dl> : <p className="mt-5 text-muted">{t("pilot.officesPending")}</p>}
        </section>

        {/* Response times */}
        <section id="sla" className="scroll-mt-4 bg-bg">
          <div className={`${wrap} py-20`}>
            <SectionHead title={c.sla.title} sub={c.sla.sub} />
            {service?.sla.length ? <>
              <ul className="mt-6 divide-y divide-border rounded-lg border border-border bg-surface">
                {service.sla.map((r) => (
                  <li key={r.priority} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_2fr] sm:items-center sm:gap-5 sm:px-5">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <PriorityBadge priority={r.priority} />
                      <span className="text-muted">{t(r.use_working_hours ? "pilot.workingHours" : "pilot.calendarHours")}</span>
                    </div>
                    <dl className="grid grid-cols-2 gap-2 tabular-nums">
                      <div><dt className="text-muted">{c.sla.first}</dt><dd className="font-semibold">{hours(r.first_response_hours)}</dd></div>
                      <div><dt className="text-muted">{c.sla.resolve}</dt><dd className="font-semibold">{hours(r.resolution_hours)}</dd></div>
                    </dl>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm text-muted">{c.sla.pausedNote}</p>
            </> : <p className="mt-5 text-muted">{t("pilot.slaPending")}</p>}
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className={`${wrap} scroll-mt-4 py-20`}>
          <div className="max-w-3xl">
            <SectionHead title={c.faq.title} />
            <div className="mt-8 divide-y divide-border border-y border-border">
              {faq.map((f) => (
                <details key={f.q} className="group">
                  <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-3 text-lg font-semibold [&::-webkit-details-marker]:hidden">
                    {f.q}
                    <ChevronDown className="h-5 w-5 shrink-0 text-muted transition-transform group-open:rotate-180" aria-hidden />
                  </summary>
                  <p className="pb-5 pr-8 leading-relaxed text-muted">{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* Closing action */}
        <section className="bg-primary-soft">
          <div className={`${wrap} flex flex-col items-start gap-6 py-16 md:flex-row md:items-center md:justify-between`}>
            <div>
              <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">{c.cta.title}</h2>
              <p className="mt-2 text-lg text-muted">{c.cta.body}</p>
            </div>
            <Link href={submitHref} className={`${primaryBtn} shrink-0`}>
              {c.cta.button}
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className={`${wrap} flex flex-col gap-4 py-10 text-sm text-muted md:flex-row md:items-center md:justify-between`}>
          <Logo />
          <p className="max-w-md">{c.footer.about}</p>
          {(service?.privacy_url || service?.data_contact) && <div className="flex flex-col gap-2">
            {service?.privacy_url && <a className="underline" href={service.privacy_url}>{t("pilot.dataInfo")}</a>}
            {service?.data_contact && <a className="underline" href={`mailto:${service.data_contact}`}>{t("pilot.dataContact")}</a>}
          </div>}
          <p>© {c.footer.rights}</p>
        </div>
      </footer>
    </div>
  );
}
