import clsx from "clsx";

/**
 * Qoldau mark: the student (mortarboard) follows an S-shaped route to the right office (node),
 * with a chat bubble for the conversation. Colours come from CSS tokens so it adapts to dark mode.
 */
export function LogoMark({ className, title = "Qoldau" }: { className?: string; title?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={clsx("shrink-0", className)} role="img" aria-label={title}>
      <path
        d="M10.5 15.2 29.2 7.6a2.2 2.2 0 0 1 1.6 0l18.7 7.6c1 .4 1 1.8 0 2.2L30.8 25a2.2 2.2 0 0 1-1.6 0L10.5 17.4c-1-.4-1-1.8 0-2.2Z"
        fill="var(--logo-ink)"
      />
      <path d="M47 18v5.5" stroke="var(--logo-ink)" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="47" cy="25.6" r="2.2" fill="var(--brand-amber)" />
      <path
        d="M30 25.5C30 31 17 30.5 17 37.5 17 44 39 41.5 39 48.5 39 53 34.5 55 29 55H15"
        fill="none"
        stroke="var(--brand-teal)"
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="55" r="5" fill="var(--brand-teal)" />
      <circle cx="12" cy="55" r="2" fill="var(--logo-paper)" />
      <path
        d="M45 28h11a5 5 0 0 1 5 5v4.5a5 5 0 0 1-5 5h-6.5L45 46v-3.6a5 5 0 0 1-4-4.9V33a5 5 0 0 1 4-5Z"
        fill="var(--brand-amber)"
      />
      <path d="M45.5 33.2h10M45.5 37.2h6.5" stroke="var(--logo-paper)" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span className={clsx("inline-flex items-center gap-2", className)}>
      <LogoMark className="h-8 w-8" />
      <span className="flex flex-col leading-tight">
        <span className="text-base font-bold text-text">Qoldau</span>
        {!compact && <span className="whitespace-nowrap text-xs text-muted">SDU University</span>}
      </span>
    </span>
  );
}
