"use client";

import clsx from "clsx";
import {
  BarChart3,
  Bell,
  BookOpen,
  BrainCircuit,
  FileDown,
  FilePlus2,
  Inbox,
  KanbanSquare,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Sun,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { useRealtime } from "@/lib/realtime";
import { useTheme } from "@/lib/theme";
import type { Lang, Role } from "@/lib/types";
import { Logo, LogoMark } from "./Logo";
import { Spinner } from "./ui";

interface NavItem {
  href: string;
  key: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: Role[];
}

const NAV: NavItem[] = [
  { href: "/dashboard", key: "nav.dashboard", icon: LayoutDashboard, roles: ["student"] },
  { href: "/requests/new", key: "nav.newRequest", icon: FilePlus2, roles: ["student"] },
  { href: "/requests", key: "nav.myRequests", icon: ListChecks, roles: ["student"] },
  { href: "/agent/board", key: "nav.board", icon: KanbanSquare, roles: ["agent", "unit_head", "admin"] },
  { href: "/agent/triage", key: "nav.triage", icon: Inbox, roles: ["agent", "unit_head", "admin"] },
  { href: "/agent/requests", key: "nav.queue", icon: ListChecks, roles: ["agent", "unit_head", "admin"] },
  { href: "/analytics", key: "nav.analytics", icon: BarChart3, roles: ["unit_head", "admin", "agent"] },
  { href: "/kb", key: "nav.kb", icon: BookOpen, roles: ["agent", "unit_head", "admin"] },
  { href: "/reports", key: "nav.reports", icon: FileDown, roles: ["unit_head", "admin"] },
  { href: "/admin", key: "nav.admin", icon: Settings, roles: ["admin"] },
  { href: "/admin/models", key: "nav.models", icon: BrainCircuit, roles: ["admin"] },
  { href: "/notifications", key: "nav.notifications", icon: Bell, roles: ["student", "agent", "unit_head", "admin"] },
];

const SIDEBAR_KEY = "qoldau.sidebar";

function NavLinks({ role, onNavigate, collapsed = false }: { role: Role; onNavigate?: () => void; collapsed?: boolean }) {
  const { t } = useI18n();
  const path = usePathname();
  const items = NAV.filter((n) => n.roles.includes(role));
  // The most specific matching entry wins (/admin/models must not also light up /admin).
  const matches = (href: string) => path === href || (href !== "/requests" && path.startsWith(href + "/"));
  const current = items.filter((n) => matches(n.href)).sort((a, b) => b.href.length - a.href.length)[0]?.href;
  return (
    <nav aria-label="Main" className="flex flex-col gap-1">
      {items.map((n) => {
        const active = n.href === current;
        return (
          <Link
            key={n.href}
            href={n.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            title={collapsed ? t(n.key) : undefined}
            className={clsx(
              "flex min-h-11 items-center gap-3 rounded-md text-[15px]",
              collapsed ? "justify-center px-0" : "px-3",
              active ? "bg-primary-soft font-semibold text-primary" : "text-text hover:bg-surface-2",
            )}
          >
            <n.icon className={clsx("h-5 w-5 shrink-0", !active && "text-muted")} />
            <span className={collapsed ? "sr-only" : undefined}>{t(n.key)}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function LangSwitch() {
  const { lang, setLang, t } = useI18n();
  return (
    <select
      aria-label={t("common.language")}
      value={lang}
      onChange={(e) => setLang(e.target.value as Lang)}
      className="min-h-11 rounded-md bg-transparent px-2 text-sm font-medium hover:bg-surface-2"
    >
      <option value="kz">KZ</option>
      <option value="ru">RU</option>
      <option value="en">EN</option>
    </select>
  );
}

export function AppShell({ children, roles }: { children: React.ReactNode; roles?: Role[] }) {
  const { user, loading, logout } = useAuth();
  const { t } = useI18n();
  const { theme, toggle } = useTheme();
  const { unread } = useRealtime();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  // Desktop sidebar can be collapsed to an icon rail; the choice is remembered per browser.
  const [collapsed, setCollapsed] = useState(false);
  const path = usePathname();

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(SIDEBAR_KEY) === "collapsed");
    } catch {}
  }, []);
  const toggleSidebar = () =>
    setCollapsed((c) => {
      try {
        localStorage.setItem(SIDEBAR_KEY, c ? "open" : "collapsed");
      } catch {}
      return !c;
    });

  useEffect(() => setOpen(false), [path]);
  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [loading, user, router, path]);
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
  }, [open]);

  if (loading || !user) return <Spinner label={t("common.loading")} />;

  const denied = roles && !roles.includes(user.role);
  const signOut = async () => {
    await logout();
    router.replace("/login");
  };
  const logoutBtn = (
    <button onClick={signOut} aria-label={t("auth.logout")} title={t("auth.logout")} className="grid h-11 w-11 shrink-0 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text">
      <LogOut className="h-5 w-5" />
    </button>
  );
  const account = (
    <div className="mt-auto flex items-center gap-2 border-t border-border pt-3">
      <div className="min-w-0 flex-1 px-3 text-sm leading-tight">
        <div className="truncate font-semibold">{user.name}</div>
        <div className="truncate text-muted">{user.unit_name ?? user.role.replace("_", " ")}</div>
      </div>
      {logoutBtn}
    </div>
  );
  const collapseBtn = (
    <button
      onClick={toggleSidebar}
      aria-label={collapsed ? t("nav.expand") : t("nav.collapse")}
      title={collapsed ? t("nav.expand") : t("nav.collapse")}
      aria-expanded={!collapsed}
      className="grid h-11 w-11 shrink-0 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text"
    >
      {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
    </button>
  );

  return (
    <div className={clsx("min-h-screen md:grid md:transition-[grid-template-columns] md:duration-200", collapsed ? "md:grid-cols-[72px_1fr]" : "md:grid-cols-[248px_1fr]")}>
      {/* Desktop sidebar: full width or an icon rail */}
      <aside className="sticky top-0 hidden h-screen flex-col gap-6 overflow-hidden border-r border-border bg-surface px-3 py-4 md:flex">
        {collapsed ? (
          <>
            <Link href="/" className="grid h-11 place-items-center" aria-label="Qoldau — SDU University">
              <LogoMark className="h-8 w-8" />
            </Link>
            <NavLinks role={user.role} collapsed />
            <div className="mt-auto flex flex-col items-center gap-1 border-t border-border pt-3">
              {collapseBtn}
              {logoutBtn}
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between gap-2 pl-3">
              <Link href="/" aria-label="Qoldau — SDU University">
                <Logo />
              </Link>
              {collapseBtn}
            </div>
            <NavLinks role={user.role} />
            {account}
          </>
        )}
      </aside>

      {/* Mobile drawer (US4): slides in from the side, background dimmed and inert */}
      <div
        className={clsx("fixed inset-0 z-40 bg-black/40 transition-opacity md:hidden", open ? "opacity-100" : "pointer-events-none opacity-0")}
        onClick={() => setOpen(false)}
        aria-hidden
      />
      <aside
        id="mobile-nav"
        aria-label={t("nav.menu")}
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col gap-6 bg-surface px-3 py-4 shadow-xl transition-transform duration-200 md:hidden",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        inert={!open}
      >
        <div className="flex items-center justify-between pl-3">
          <Logo />
          <button onClick={() => setOpen(false)} aria-label={t("nav.close")} className="grid h-11 w-11 place-items-center rounded-md hover:bg-surface-2">
            <X className="h-5 w-5" />
          </button>
        </div>
        <NavLinks role={user.role} onNavigate={() => setOpen(false)} />
        {account}
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-1 border-b border-border bg-surface px-2 py-1.5 md:bg-bg md:px-6">
          <button
            className="grid h-11 w-11 place-items-center rounded-md hover:bg-surface-2 md:hidden"
            aria-label={t("nav.menu")}
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          <Link href="/" className="md:hidden" aria-label="Qoldau">
            <Logo compact />
          </Link>
          <div className="ml-auto flex items-center gap-1">
            <LangSwitch />
            <button onClick={toggle} aria-label={t("common.theme")} className="grid h-11 w-11 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text">
              {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
            <Link
              href="/notifications"
              aria-label={`${t("nav.notifications")}${unread ? ` (${unread})` : ""}`}
              className="relative grid h-11 w-11 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text"
            >
              <Bell className="h-5 w-5" />
              {unread > 0 && (
                <span className="absolute right-1 top-1 grid min-w-5 place-items-center rounded-full bg-critical px-1 text-[11px] font-bold text-white">
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
            </Link>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 md:py-8">
          {denied ? (
            <div role="alert" className="rounded-lg bg-critical/10 p-6 text-center font-semibold text-critical">
              {t("access.denied")}
            </div>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
