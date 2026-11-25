"use client";

import { ListFilter, X } from "lucide-react";
import { useId, useRef, useState, type ComponentPropsWithoutRef, type ReactNode } from "react";
import { useI18n } from "@/lib/i18n";
import { Button, Input, Label, Select } from "./ui";

export function FilterSelect({ label, wide, ...props }: Omit<ComponentPropsWithoutRef<typeof Select>, "id"> & {
  label: string;
  wide?: boolean;
}) {
  const id = useId();
  return (
    <div className={wide ? "col-span-full min-w-0" : "min-w-0"}>
      <Label htmlFor={id}>{label}</Label>
      <Select {...props} id={id} />
    </div>
  );
}

export function FilterDate({ label, ...props }: Omit<ComponentPropsWithoutRef<typeof Input>, "id" | "type"> & {
  label: string;
}) {
  const id = useId();
  return (
    <div className="min-w-0">
      <Label htmlFor={id}>{label}</Label>
      <Input {...props} id={id} type="date" />
    </div>
  );
}

export function FilterDialog<T extends Record<string, string>>({
  value,
  defaults,
  onApply,
  children,
}: {
  value: T;
  defaults: T;
  onApply: (value: T) => void;
  children: (draft: T, update: (patch: Partial<T>) => void) => ReactNode;
}) {
  const { t } = useI18n();
  const id = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [draft, setDraft] = useState(value);
  const count = Object.keys(value).filter((key) => value[key] !== defaults[key]).length;
  const close = () => dialog.current?.close();

  return (
    <>
      <Button
        ref={trigger}
        type="button"
        variant="secondary"
        size="sm"
        className="shrink-0 whitespace-nowrap"
        aria-haspopup="dialog"
        aria-controls={id}
        onClick={() => {
          setDraft(value);
          dialog.current?.showModal();
        }}
      >
        <ListFilter className="size-4" aria-hidden />
        {t("common.filters")}
        {count > 0 && (
          <span className="rounded-full bg-primary-soft px-1.5 text-xs leading-5 text-primary tabular-nums">
            {count}
          </span>
        )}
      </Button>
      <dialog
        ref={dialog}
        id={id}
        aria-labelledby={`${id}-title`}
        onClose={() => trigger.current?.focus()}
        className="fixed inset-x-0 top-auto bottom-0 mx-auto mt-auto mb-0 max-h-[90dvh] w-full max-w-none overflow-y-auto overscroll-contain rounded-t-xl border border-border bg-surface p-0 text-text shadow-xl backdrop:bg-black/45 sm:inset-0 sm:m-auto sm:max-w-md sm:rounded-xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onApply(draft);
            close();
          }}
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-2 sm:px-5">
            <h2 id={`${id}-title`} className="text-lg font-semibold">{t("common.filters")}</h2>
            <Button type="button" variant="ghost" size="sm" aria-label={t("common.close")} onClick={close}>
              <X className="size-5" aria-hidden />
            </Button>
          </div>
          <div className="grid gap-3 p-4 min-[360px]:grid-cols-2 sm:p-5">
            {children(draft, (patch) => setDraft((prev) => ({ ...prev, ...patch })))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-3 sm:px-5">
            <Button type="button" variant="ghost" size="sm" onClick={() => setDraft(defaults)}>
              {t("common.clear")}
            </Button>
            <Button type="submit" size="sm">{t("common.apply")}</Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
