"use client";

import { Bold, Heading3, Italic, Link2, List, Pilcrow } from "lucide-react";
import { useRef } from "react";
import { useI18n } from "@/lib/i18n";
import { Textarea } from "./ui";

const TAGS = new Set(["P", "BR", "STRONG", "B", "EM", "I", "U", "UL", "OL", "LI", "A", "H3", "H4", "BLOCKQUOTE", "CODE"]);

/** Same allow-list as the API (bleach). Parsed in an inert document, so nothing runs while cleaning. */
export function cleanHtml(html: string): string {
  if (typeof window === "undefined") return "";
  const doc = new DOMParser().parseFromString(`<body>${html}</body>`, "text/html");
  const walk = (node: Element) => {
    for (const child of Array.from(node.children)) {
      walk(child);
      if (!TAGS.has(child.tagName)) {
        if (["SCRIPT", "STYLE", "IFRAME", "OBJECT"].includes(child.tagName)) child.remove();
        else child.replaceWith(...Array.from(child.childNodes));
        continue;
      }
      for (const attr of Array.from(child.attributes)) {
        const keep = child.tagName === "A" && (attr.name === "title" || (attr.name === "href" && /^(https?:|mailto:)/i.test(attr.value.trim())));
        if (!keep) child.removeAttribute(attr.name);
      }
      if (child.tagName === "A") {
        child.setAttribute("rel", "noopener noreferrer");
        child.setAttribute("target", "_blank");
      }
    }
  };
  walk(doc.body);
  return doc.body.innerHTML;
}

/** Renders FAQ HTML. The API sanitises bodies before storing them; cleanHtml() is a second line of defence. */
export function SafeHtml({ html, className }: { html: string; className?: string }) {
  return <div className={`rich ${className ?? ""}`} dangerouslySetInnerHTML={{ __html: cleanHtml(html) }} />;
}

/** Small rich-text editor: an HTML source box with formatting buttons and a live preview. */
export function RichTextEditor({ id, value, onChange, invalid }: { id: string; value: string; onChange: (v: string) => void; invalid?: boolean }) {
  const { t } = useI18n();
  const ref = useRef<HTMLTextAreaElement>(null);

  function wrap(before: string, after: string, fallback: string) {
    const el = ref.current;
    if (!el) return;
    const { selectionStart: s, selectionEnd: e } = el;
    const selected = value.slice(s, e) || fallback;
    const next = value.slice(0, s) + before + selected + after + value.slice(e);
    onChange(next);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(s + before.length, s + before.length + selected.length);
    });
  }

  // [label, icon, before, after, placeholder text]
  const tools = [
    [t("kb.tb.bold"), Bold, "<strong>", "</strong>", "text"],
    [t("kb.tb.italic"), Italic, "<em>", "</em>", "text"],
    [t("kb.tb.heading"), Heading3, "<h3>", "</h3>", "Heading"],
    [t("kb.tb.paragraph"), Pilcrow, "<p>", "</p>", ""],
    [t("kb.tb.list"), List, "<ul>\n  <li>", "</li>\n</ul>", "item"],
    [t("kb.tb.link"), Link2, '<a href="https://">', "</a>", "link"],
  ] as const;

  return (
    <div className="space-y-2">
      <div role="toolbar" aria-label={t("kb.body")} aria-controls={id} className="flex flex-wrap gap-1">
        {tools.map(([label, Icon, before, after, fallback]) => (
          <button
            key={label}
            type="button"
            onClick={() => wrap(before, after, fallback)}
            aria-label={label}
            title={label}
            className="grid h-11 w-11 place-items-center rounded-md border border-border hover:bg-surface-2"
          >
            <Icon className="h-4 w-4" aria-hidden />
          </button>
        ))}
      </div>
      <Textarea ref={ref} id={id} rows={8} value={value} invalid={invalid} onChange={(e) => onChange(e.target.value)} className="font-mono text-sm" />
      <div>
        <div className="mb-1 text-xs font-semibold text-muted">{t("kb.preview")}</div>
        <div className="rounded-md border border-dashed border-border p-3">
          <SafeHtml html={value} />
        </div>
      </div>
    </div>
  );
}
