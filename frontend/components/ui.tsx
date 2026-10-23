"use client";

import clsx from "clsx";
import { Loader2, X } from "lucide-react";
import { forwardRef, useEffect, useRef } from "react";

type BtnVariant = "primary" | "secondary" | "ghost" | "danger";

export const Button = forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; loading?: boolean; size?: "sm" | "md" }
>(function Button({ variant = "primary", loading, size = "md", className, children, disabled, ...rest }, ref) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-md font-semibold transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-3 text-sm" : "px-4 text-sm",
        variant === "primary" && "bg-primary text-primary-fg hover:bg-primary/90 active:bg-primary/80",
        variant === "secondary" && "bg-surface-2 text-text hover:bg-border",
        variant === "ghost" && "text-text hover:bg-surface-2",
        variant === "danger" && "bg-critical text-white hover:bg-critical/90",
        className,
      )}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

export function Card({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("rounded-lg border border-border bg-surface p-5", className)} {...rest}>
      {children}
    </div>
  );
}

export function Badge({ className, children, ...rest }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={clsx("inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium whitespace-nowrap", className)}
      {...rest}
    >
      {children}
    </span>
  );
}

// Fields are full width unless the caller sets an explicit width class.
const widthCls = (className?: string) => (/(^|\s)(\w+:)?w-/.test(className ?? "") ? "" : "w-full");
const fieldCls =
  "rounded-md border bg-surface px-3 py-2.5 text-[15px] text-text placeholder:text-muted min-h-11 " +
  "focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/25";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }>(
  function Input({ invalid, className, ...rest }, ref) {
    return (
      <input
        ref={ref}
        aria-invalid={invalid || undefined}
        className={clsx(fieldCls, widthCls(className), invalid ? "border-critical" : "border-border", className)}
        {...rest}
      />
    );
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }
>(function Textarea({ invalid, className, ...rest }, ref) {
  return (
    <textarea
      ref={ref}
      aria-invalid={invalid || undefined}
      className={clsx(fieldCls, widthCls(className), "min-h-32", invalid ? "border-critical" : "border-border", className)}
      {...rest}
    />
  );
});

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean }>(
  function Select({ invalid, className, children, ...rest }, ref) {
    return (
      <select
        ref={ref}
        aria-invalid={invalid || undefined}
        className={clsx(fieldCls, widthCls(className), invalid ? "border-critical" : "border-border", className)}
        {...rest}
      >
        {children}
      </select>
    );
  },
);

export function Label({ className, ...rest }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={clsx("mb-1.5 block text-sm font-semibold", className)} {...rest} />;
}

export function FieldError({ id, children }: { id?: string; children?: React.ReactNode }) {
  if (!children) return null;
  return (
    <p id={id} role="alert" className="mt-1 text-sm font-medium text-critical">
      {children}
    </p>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 p-8 text-muted">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg bg-surface-2 px-6 py-10 text-center text-muted">{children}</div>;
}

export function Modal({
  open,
  onClose,
  title,
  children,
  labelledBy = "modal-title",
  size = "md",
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  labelledBy?: string;
  size?: "md" | "lg" | "xl";
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    ref.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        className={clsx(
          "max-h-[90vh] w-full overflow-y-auto rounded-t-lg bg-surface p-6 shadow-xl sm:rounded-lg",
          size === "md" ? "sm:max-w-md" : size === "lg" ? "sm:max-w-2xl" : "sm:max-w-4xl",
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-4">
          {title && (
            <h2 id={labelledBy} className="text-lg font-semibold">
              {title}
            </h2>
          )}
          <button onClick={onClose} aria-label="Close" className="ml-auto -mr-2 -mt-2 grid h-11 w-11 place-items-center rounded-md text-muted hover:bg-surface-2 hover:text-text">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Toast({ message, tone = "info", onDone }: { message: string; tone?: "info" | "error"; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3500);
    return () => clearTimeout(t);
  }, [onDone, message]);
  return (
    <div
      role="status"
      className={clsx(
        "fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-md px-4 py-3 text-sm font-medium shadow-lg",
        tone === "error" ? "bg-critical text-white" : "bg-text text-bg",
      )}
    >
      {message}
    </div>
  );
}
