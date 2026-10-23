"use client";

import { ChevronDown, Moon, Sun } from "lucide-react";
import Link from "next/link";
import { PriorityBadge } from "@/components/badges";
import { RouteDemo } from "@/components/landing/RouteDemo";
import { Logo } from "@/components/Logo";
import { homeFor, useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { LANDING } from "@/lib/landing-copy";
import { useTheme } from "@/lib/theme";
import type { Lang, Priority } from "@/lib/types";

const wrap = "mx-auto max-w-6xl px-4 sm:px-6";
const primaryBtn =
  "inline-flex min-h-12 items-center justify-center rounded-md bg-primary px-6 font-semibold text-primary-fg transition-colors hover:bg-primary/90";

function LangToggle() {
  const { lang, setLang } = useI18n();
  return (
    <div role="group" aria-label="Language" className="flex">
      {(["kz", "ru", "en"] as Lang[]).map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`min-h-11 min-w-10 rounded-md px-1.5 text-sm transition-colors ${
            lang === l ? "font-bold text-text" : "text-muted hover:bg-surface-2 hover:text-text"
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function SectionHead({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="max-w-2xl">
      <h2 className="text-3xl font-bold tracking-tight">{title}</h2>
      {sub && <p className="mt-3 text-lg text-muted">{sub}</p>}
    </div>
  );
}

export default function Landing() {
  const { lang } = useI18n();
  const { user } = useAuth();
  const { theme, toggle } = useTheme();
  const c = LANDING[lang];

  const submitHref = user ? (user.role === "student" ? "/requests/new" : homeFor(user.role)) : "/login?next=/requests/new";
  const portalHref = user ? homeFor(user.role) : "/login";

  return (
    <div className="min-h-screen bg-surface">
      <a href="#main" className="sr-only z-50 rounded-md bg-surface px-4 py-3 font-semibold focus:not-sr-only focus:fixed focus:left-4 focus:top-4">
        {c.nav.skip}
      </a>

      <header className="border-b border-border">
        <div className={`${wrap} flex h-16 items-center gap-6`}>
          <Link href="/" aria-label="Qoldau — SDU University">
            <Logo />
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
            <div className="hidden sm:block">
              <LangToggle />
            </div>
            <button onClick={toggle} aria-label="Toggle theme" className="grid h-11 w-11 shrink-0 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text">
              {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <Link href={portalHref} className="ml-1 inline-flex min-h-11 shrink-0 items-center rounded-md bg-surface-2 px-4 text-sm font-semibold hover:bg-border">
              {user ? c.nav.openPortal : c.nav.signIn}
            </Link>
          </div>
        </div>
      </header>

      <main id="main">
        {/* Hero: what it is, what to do, and a real example */}
        <section className={`${wrap} grid items-center gap-12 py-16 lg:grid-cols-[1.2fr_1fr] lg:py-24`}>
          <div>
            <h1 className="text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
              {c.hero.title1} <br className="hidden sm:block" />
              {c.hero.title2}
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">{c.hero.sub}</p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link href={submitHref} className={primaryBtn}>
                {c.hero.ctaStudent}
              </Link>
              <Link href="/login" className="inline-flex min-h-12 items-center justify-center rounded-md px-4 font-semibold text-primary hover:bg-surface-2">
                {c.hero.ctaStaff}
              </Link>
            </div>
            <p className="mt-4 text-sm text-muted">{c.hero.note}</p>
            <div className="mt-6 sm:hidden">
              <LangToggle />
            </div>
          </div>
          <div className="flex justify-center lg:justify-end">
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
          <dl className="mt-10 grid gap-x-10 gap-y-7 sm:grid-cols-2 lg:grid-cols-3">
            {c.offices.units.map((u) => (
              <div key={u.name}>
                <dt className="font-semibold">{u.name}</dt>
                <dd className="mt-1 text-muted">{u.topics}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* Response times */}
        <section id="sla" className="scroll-mt-4 bg-bg">
          <div className={`${wrap} py-20`}>
            <SectionHead title={c.sla.title} sub={c.sla.sub} />
            <div className="mt-10 overflow-x-auto rounded-lg border border-border bg-surface">
              <table className="w-full min-w-[560px] text-left">
                <thead className="text-sm text-muted">
                  <tr>
                    <th scope="col" className="px-5 py-3 font-medium">{c.sla.priority}</th>
                    <th scope="col" className="px-5 py-3 font-medium">{c.sla.first}</th>
                    <th scope="col" className="px-5 py-3 font-medium">{c.sla.resolve}</th>
                    <th scope="col" className="px-5 py-3 font-medium">{c.sla.when}</th>
                  </tr>
                </thead>
                <tbody>
                  {c.sla.rows.map((r) => (
                    <tr key={r.p} className="border-t border-border">
                      <td className="px-5 py-4">
                        <PriorityBadge priority={r.p as Priority} />
                      </td>
                      <td className="px-5 py-4 font-semibold">{r.first}</td>
                      <td className="px-5 py-4 font-semibold">{r.resolve}</td>
                      <td className="px-5 py-4 text-muted">{r.when}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-4 text-sm text-muted">{c.sla.pausedNote}</p>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className={`${wrap} scroll-mt-4 py-20`}>
          <div className="max-w-3xl">
            <SectionHead title={c.faq.title} />
            <div className="mt-8 divide-y divide-border border-y border-border">
              {c.faq.items.map((f) => (
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
          <p>© {c.footer.rights}</p>
        </div>
      </footer>
    </div>
  );
}
