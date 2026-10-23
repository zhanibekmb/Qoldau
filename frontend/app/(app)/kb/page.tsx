"use client";

import clsx from "clsx";
import { Archive, History, Pencil, Plus, Search, Send, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Guard } from "@/components/Guard";
import { RichTextEditor } from "@/components/RichText";
import { Badge, Button, Card, Empty, FieldError, Input, Label, Modal, Select, Spinner, Textarea, Toast } from "@/components/ui";
import { api, ApiError, qs } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { CategoryMeta, FAQArticle, FAQStatus, FAQVersion, Lang, Page, ReplyTemplate, User } from "@/lib/types";

const LANGS: Lang[] = ["kz", "ru", "en"];
const PLACEHOLDERS = ["{student_name}", "{request_id}", "{unit}", "{agent_name}"];
const STATUS_CLS: Record<FAQStatus, string> = {
  draft: "bg-warn/12 text-warn",
  published: "bg-ok/12 text-ok",
  archived: "bg-surface-2 text-muted",
};

const canPublish = (u: User, unitId: number | null) => u.role === "admin" || (u.role === "unit_head" && unitId !== null && u.unit_id === unitId);
const plain = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();

/** Word-level diff (LCS) between two versions of an article. */
function diffWords(a: string, b: string): { t: string; k: "same" | "add" | "del" }[] {
  const x = a.split(" ");
  const y = b.split(" ");
  const n = x.length;
  const m = y.length;
  const dp = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = x[i] === y[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: { t: string; k: "same" | "add" | "del" }[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (x[i] === y[j]) {
      out.push({ t: x[i++], k: "same" });
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) out.push({ t: x[i++], k: "del" });
    else out.push({ t: y[j++], k: "add" });
  }
  while (i < n) out.push({ t: x[i++], k: "del" });
  while (j < m) out.push({ t: y[j++], k: "add" });
  return out;
}

function StatusBadge({ status }: { status: FAQStatus }) {
  const { t } = useI18n();
  return <Badge className={STATUS_CLS[status]}>{t(`kb.st.${status}`)}</Badge>;
}

// ---------------- FAQ editor ----------------
interface Draft {
  title: string;
  body: string;
  tags: string;
  category_id: string;
}

const emptyDraft = (category = ""): Draft => ({ title: "", body: "", tags: "", category_id: category });
const toDraft = (a: FAQArticle): Draft => ({ title: a.title, body: a.body, tags: a.tags.join(", "), category_id: a.category_id ? String(a.category_id) : "" });

function FaqEditor({ slug, startLang, user, cats, onClose, onChanged }: { slug: string | null; startLang: Lang; user: User; cats: CategoryMeta[]; onClose: () => void; onChanged: () => void }) {
  const { t, lang: uiLang } = useI18n();
  const [groupSlug, setGroupSlug] = useState(slug);
  const [rows, setRows] = useState<Partial<Record<Lang, FAQArticle>>>({});
  const [drafts, setDrafts] = useState<Record<Lang, Draft>>({ kz: emptyDraft(), ru: emptyDraft(), en: emptyDraft() });
  const [lang, setLang] = useState<Lang>(startLang);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [versions, setVersions] = useState<FAQVersion[] | null>(null);
  const [loading, setLoading] = useState(!!slug);

  const loadGroup = useCallback(async (s: string) => {
    const page = await api<Page<FAQArticle>>(`/admin/faq${qs({ slug: s, page_size: 10 })}`);
    const byLang: Partial<Record<Lang, FAQArticle>> = {};
    page.items.forEach((a) => (byLang[a.language] = a));
    setRows(byLang);
    const shared = page.items[0]?.category_id ? String(page.items[0].category_id) : "";
    setDrafts({
      kz: byLang.kz ? toDraft(byLang.kz) : emptyDraft(shared),
      ru: byLang.ru ? toDraft(byLang.ru) : emptyDraft(shared),
      en: byLang.en ? toDraft(byLang.en) : emptyDraft(shared),
    });
    setLoading(false);
  }, []);

  useEffect(() => {
    if (slug) loadGroup(slug).catch(() => setError(t("common.error")));
  }, [slug, loadGroup, t]);

  const row = rows[lang];
  const draft = drafts[lang];
  const set = (patch: Partial<Draft>) => setDrafts((d) => ({ ...d, [lang]: { ...d[lang], ...patch } }));
  const publishAllowed = row ? canPublish(user, row.unit_id) : user.role === "admin" || user.role === "unit_head";
  const mayEdit = !row || publishAllowed || (row.status === "draft" && row.author?.id === user.id);

  async function save(): Promise<FAQArticle | null> {
    setError("");
    if (draft.title.trim().length < 3 || plain(draft.body).length < 10) {
      setError(t("form.tooShort", { n: 10 }));
      return null;
    }
    const body = {
      slug: groupSlug,
      title: draft.title.trim(),
      body: draft.body,
      language: lang,
      category_id: draft.category_id ? Number(draft.category_id) : null,
      tags: draft.tags.split(",").map((x) => x.trim()).filter(Boolean),
    };
    const saved = row
      ? await api<FAQArticle>(`/admin/faq/${row.id}`, { method: "PUT", json: body })
      : await api<FAQArticle>("/admin/faq", { method: "POST", json: body });
    setGroupSlug(saved.slug);
    setRows((r) => ({ ...r, [lang]: saved }));
    setDrafts((d) => ({ ...d, [lang]: toDraft(saved) }));
    setVersions(null);
    onChanged();
    return saved;
  }

  async function act(kind: "save" | "publish" | "archive" | "delete") {
    setBusy(kind);
    try {
      if (kind === "delete" && row) {
        await api(`/admin/faq/${row.id}`, { method: "DELETE" });
        setRows((r) => ({ ...r, [lang]: undefined }));
        onChanged();
        return;
      }
      const saved = kind === "archive" ? row! : await save();
      if (!saved || kind === "save") return;
      const out = await api<FAQArticle>(`/admin/faq/${saved.id}/${kind}`, { method: "POST" });
      setRows((r) => ({ ...r, [lang]: out }));
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(null);
    }
  }

  async function toggleHistory() {
    if (versions) return setVersions(null);
    if (row) setVersions(await api<FAQVersion[]>(`/admin/faq/${row.id}/versions`).catch(() => []));
  }

  return (
    <Modal open onClose={onClose} size="xl" title={slug ? t("kb.editArticle") : t("kb.new")}>
      {loading ? (
        <Spinner />
      ) : (
        <div className="space-y-4">
          <div role="tablist" aria-label={t("kb.translations")} className="flex gap-2">
            {LANGS.map((l) => (
              <Button key={l} role="tab" aria-selected={lang === l} size="sm" variant={lang === l ? "primary" : "secondary"} onClick={() => { setLang(l); setVersions(null); setError(""); }}>
                {l.toUpperCase()}
                {rows[l] ? <span className={clsx("h-2 w-2 rounded-full", rows[l]!.status === "published" ? "bg-ok" : rows[l]!.status === "draft" ? "bg-warn" : "bg-muted")} aria-label={t(`kb.st.${rows[l]!.status}`)} /> : <span className="text-xs opacity-70">+</span>}
              </Button>
            ))}
          </div>

          {row ? (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
              <StatusBadge status={row.status} />
              <span>{t("kb.version", { n: row.version })}</span>
              {row.author && <span>{t("kb.by", { name: row.author.name })}</span>}
              <span>{t("kb.views")}: {row.views}</span>
              <span>{t("kb.helpful")}: {row.helpful_pct === null ? "—" : `${row.helpful_pct}%`} ({row.helpful_yes}/{row.helpful_yes + row.helpful_no})</span>
              {row.unit_name && <span>{row.unit_name}</span>}
            </div>
          ) : (
            <p className="text-sm text-muted">{t("kb.noTranslation", { lang: lang.toUpperCase() })}</p>
          )}
          {user.role === "agent" && <p className="rounded-md bg-surface-2 px-3 py-2 text-sm">{t("kb.agentHint")}</p>}

          <fieldset disabled={!mayEdit} className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-[1fr_16rem]">
              <div>
                <Label htmlFor="faq-title">{t("kb.articleTitle")}</Label>
                <Input id="faq-title" lang={lang === "kz" ? "kk" : lang} value={draft.title} maxLength={200} onChange={(e) => set({ title: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="faq-cat">{t("kb.category")}</Label>
                <Select id="faq-cat" value={draft.category_id} onChange={(e) => set({ category_id: e.target.value })}>
                  <option value="">—</option>
                  {cats.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="faq-body">{t("kb.body")}</Label>
              <RichTextEditor id="faq-body" value={draft.body} onChange={(v) => set({ body: v })} />
            </div>
            <div>
              <Label htmlFor="faq-tags">{t("kb.tags")}</Label>
              <Input id="faq-tags" value={draft.tags} onChange={(e) => set({ tags: e.target.value })} />
            </div>
          </fieldset>

          <FieldError>{error}</FieldError>
          <div className="flex flex-wrap gap-2">
            {mayEdit && (
              // Editing a published article keeps it published (and re-indexes it).
              <Button variant={row?.status === "published" ? "primary" : "secondary"} loading={busy === "save"} onClick={() => act("save")}>
                {row?.status === "published" ? t("common.save") : t("kb.saveDraft")}
              </Button>
            )}
            {publishAllowed && row?.status !== "published" && (
              <Button loading={busy === "publish"} onClick={() => act("publish")}>
                <Send className="h-4 w-4" aria-hidden /> {t("kb.publish")}
              </Button>
            )}
            {publishAllowed && row && row.status !== "archived" && (
              <Button variant="ghost" loading={busy === "archive"} onClick={() => act("archive")}>
                <Archive className="h-4 w-4" aria-hidden /> {t("kb.archive")}
              </Button>
            )}
            {row && (
              <Button variant="ghost" aria-expanded={!!versions} onClick={toggleHistory}>
                <History className="h-4 w-4" aria-hidden /> {t("kb.history")}
              </Button>
            )}
            {row?.status === "draft" && mayEdit && (
              <Button variant="ghost" className="ml-auto text-critical" loading={busy === "delete"} onClick={() => act("delete")}>
                <Trash2 className="h-4 w-4" aria-hidden /> {t("common.delete")}
              </Button>
            )}
          </div>

          {versions && (
            <section aria-label={t("kb.history")} className="space-y-3 border-t border-border pt-3">
              <p className="flex gap-3 text-xs text-muted">
                <span className="rounded bg-ok/15 px-1 text-ok">{t("kb.added")}</span>
                <span className="rounded bg-critical/10 px-1 text-critical line-through">{t("kb.removed")}</span>
              </p>
              {versions.map((v, i) => {
                const prev = versions[i + 1];
                const parts = prev ? diffWords(`${prev.title} — ${plain(prev.body)}`, `${v.title} — ${plain(v.body)}`) : null;
                return (
                  <div key={v.id} className="rounded-md border border-border p-3 text-sm">
                    <div className="mb-1 flex flex-wrap gap-x-3 text-xs text-muted">
                      <span className="font-semibold text-text">{t("kb.version", { n: v.version })}</span>
                      <span>{fmtDate(v.created_at, uiLang)}</span>
                      {v.editor && <span>{t("kb.by", { name: v.editor.name })}</span>}
                    </div>
                    <p className="leading-relaxed">
                      {parts
                        ? parts.map((p, k) => (
                            <span key={k} className={clsx(p.k === "add" && "rounded bg-ok/15 text-ok", p.k === "del" && "rounded bg-critical/10 text-critical line-through")}>
                              {p.t}{" "}
                            </span>
                          ))
                        : `${v.title} — ${plain(v.body)}`}
                    </p>
                  </div>
                );
              })}
            </section>
          )}
        </div>
      )}
    </Modal>
  );
}

// ---------------- templates ----------------
function TemplateEditor({ tpl, cats, onClose, onSaved }: { tpl: ReplyTemplate | "new"; cats: CategoryMeta[]; onClose: () => void; onSaved: () => void }) {
  const { t } = useI18n();
  const init = tpl === "new" ? null : tpl;
  const [title, setTitle] = useState(init?.title ?? "");
  const [body, setBody] = useState(init?.body ?? "");
  const [language, setLanguage] = useState<Lang>(init?.language ?? "en");
  const [category, setCategory] = useState(init?.category_id ? String(init.category_id) : "");
  const [active, setActive] = useState(init?.is_active ?? true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  function insertPh(ph: string) {
    const el = ref.current;
    const at = el ? el.selectionStart : body.length;
    setBody(body.slice(0, at) + ph + body.slice(el ? el.selectionEnd : at));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(at + ph.length, at + ph.length);
    });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const json = { title: title.trim(), body, language, category_id: category ? Number(category) : null, is_active: active };
    try {
      if (init) await api(`/admin/reply-templates/${init.id}`, { method: "PUT", json });
      else await api("/admin/reply-templates", { method: "POST", json });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} size="lg" title={init ? t("kb.editTemplate") : t("kb.newTemplate")}>
      <form onSubmit={save} className="space-y-3">
        <div>
          <Label htmlFor="tpl-title">{t("kb.articleTitle")}</Label>
          <Input id="tpl-title" value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} required minLength={3} />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="tpl-lang">{t("kb.language")}</Label>
            <Select id="tpl-lang" value={language} onChange={(e) => setLanguage(e.target.value as Lang)}>
              {LANGS.map((l) => (
                <option key={l} value={l}>
                  {l.toUpperCase()}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="tpl-cat">{t("kb.category")}</Label>
            <Select id="tpl-cat" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">—</option>
              {cats.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>
        </div>
        <div>
          <Label htmlFor="tpl-body">{t("kb.body")}</Label>
          <div className="mb-2 flex flex-wrap items-center gap-1" aria-label={t("kb.placeholders")}>
            <span className="mr-1 text-xs text-muted">{t("kb.placeholders")}:</span>
            {PLACEHOLDERS.map((ph) => (
              <button key={ph} type="button" onClick={() => insertPh(ph)} className="min-h-11 rounded-full bg-primary-soft px-3 font-mono text-xs text-primary hover:bg-primary/15">
                {ph}
              </button>
            ))}
          </div>
          <Textarea ref={ref} id="tpl-body" rows={9} value={body} lang={language === "kz" ? "kk" : language} onChange={(e) => setBody(e.target.value)} maxLength={2000} />
        </div>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" className="h-5 w-5" checked={active} onChange={(e) => setActive(e.target.checked)} /> {t("kb.active")}
        </label>
        <FieldError>{error}</FieldError>
        <div className="flex gap-2">
          <Button type="submit" loading={busy}>
            {t("common.save")}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------- page ----------------
function KbView() {
  const { user } = useAuth();
  const { t, lang: uiLang } = useI18n();
  const [tab, setTab] = useState<"faq" | "templates">("faq");
  const [cats, setCats] = useState<CategoryMeta[]>([]);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [language, setLanguage] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [faq, setFaq] = useState<Page<FAQArticle> | null>(null);
  const [templates, setTemplates] = useState<ReplyTemplate[] | null>(null);
  const [editing, setEditing] = useState<{ slug: string | null; lang: Lang } | null>(null);
  const [editingTpl, setEditingTpl] = useState<ReplyTemplate | "new" | null>(null);
  const [toast, setToast] = useState("");

  useEffect(() => {
    api<CategoryMeta[]>("/meta/categories").then(setCats).catch(() => {});
  }, []);
  useEffect(() => {
    const id = setTimeout(() => {
      setQuery(q.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(id);
  }, [q]);

  const load = useCallback(() => {
    if (tab === "faq")
      api<Page<FAQArticle>>(`/admin/faq${qs({ q: query, status, language, category_id: category, page, page_size: 20 })}`)
        .then(setFaq)
        .catch(() => setFaq({ items: [], total: 0, page: 1, page_size: 20, pages: 1 }));
    else
      api<ReplyTemplate[]>(`/admin/reply-templates${qs({ q: query, language, category_id: category })}`)
        .then(setTemplates)
        .catch(() => setTemplates([]));
  }, [tab, query, status, language, category, page]);
  useEffect(load, [load]);

  const canEditTpl = useMemo(() => (tpl: ReplyTemplate) => !!user && (canPublish(user, tpl.unit_id) || tpl.author_id === user.id), [user]);
  if (!user) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("nav.kb")}</h1>
        {tab === "faq" ? (
          <Button onClick={() => setEditing({ slug: null, lang: user.language })}>
            <Plus className="h-4 w-4" aria-hidden /> {t("kb.new")}
          </Button>
        ) : (
          <Button onClick={() => setEditingTpl("new")}>
            <Plus className="h-4 w-4" aria-hidden /> {t("kb.newTemplate")}
          </Button>
        )}
      </div>
      <div role="tablist" className="flex gap-2">
        {(["faq", "templates"] as const).map((k) => (
          <Button key={k} role="tab" aria-selected={tab === k} size="sm" variant={tab === k ? "primary" : "secondary"} onClick={() => setTab(k)}>
            {k === "faq" ? t("kb.tabFaq") : t("kb.tabTemplates")}
          </Button>
        ))}
      </div>
      {user.role === "agent" && tab === "faq" && <p className="text-sm text-muted">{t("kb.agentHint")}</p>}

      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-60 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <Input aria-label={t("common.search")} placeholder={t("kb.searchPh")} value={q} onChange={(e) => setQ(e.target.value)} className="pl-9" />
        </div>
        {tab === "faq" && (
          <Select aria-label={t("kb.status")} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="w-auto">
            <option value="">{t("kb.allStatuses")}</option>
            {(["draft", "published", "archived"] as const).map((s) => (
              <option key={s} value={s}>
                {t(`kb.st.${s}`)}
              </option>
            ))}
          </Select>
        )}
        <Select aria-label={t("kb.language")} value={language} onChange={(e) => { setLanguage(e.target.value); setPage(1); }} className="w-auto">
          <option value="">{t("kb.allLanguages")}</option>
          {LANGS.map((l) => (
            <option key={l} value={l}>
              {l.toUpperCase()}
            </option>
          ))}
        </Select>
        <Select aria-label={t("kb.category")} value={category} onChange={(e) => { setCategory(e.target.value); setPage(1); }} className="w-auto max-w-[16rem]">
          <option value="">{t("an.allCategories")}</option>
          {cats.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      {tab === "faq" ? (
        !faq ? (
          <Spinner label={t("common.loading")} />
        ) : faq.items.length === 0 ? (
          <Empty>{t("kb.empty")}</Empty>
        ) : (
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs text-muted">
                <tr>
                  <th className="p-3 font-medium">{t("kb.articleTitle")}</th>
                  <th className="p-3 font-medium">{t("kb.language")}</th>
                  <th className="p-3 font-medium">{t("kb.category")}</th>
                  <th className="p-3 font-medium">{t("kb.status")}</th>
                  <th className="p-3 text-right font-medium">{t("kb.views")}</th>
                  <th className="p-3 text-right font-medium">{t("kb.helpful")}</th>
                  <th className="p-3 font-medium">{t("kb.updated")}</th>
                  <th className="p-3" />
                </tr>
              </thead>
              <tbody>
                {faq.items.map((a) => (
                  <tr key={a.id} className="border-t border-border align-top">
                    <td className="p-3">
                      <div className="font-medium">{a.title}</div>
                      <div className="text-xs text-muted">{a.unit_name ?? "—"}</div>
                    </td>
                    <td className="p-3 uppercase">{a.language}</td>
                    <td className="p-3">{a.category_name ?? "—"}</td>
                    <td className="p-3">
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="p-3 text-right tabular-nums">{a.views}</td>
                    <td className="p-3 text-right tabular-nums">{a.helpful_pct === null ? "—" : `${a.helpful_pct}%`}</td>
                    <td className="whitespace-nowrap p-3 text-muted">{fmtDate(a.updated_at, uiLang, false)}</td>
                    <td className="p-1 text-right">
                      <button aria-label={`${t("common.edit")}: ${a.title}`} className="inline-grid h-11 w-11 place-items-center rounded-md hover:bg-surface-2" onClick={() => setEditing({ slug: a.slug, lang: a.language })}>
                        <Pencil className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {faq.pages > 1 && (
              <div className="flex items-center justify-between border-t border-border p-2 text-sm">
                <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                  {t("common.prev")}
                </Button>
                <span className="text-muted">
                  {t("common.page")} {faq.page} {t("common.of")} {faq.pages}
                </span>
                <Button size="sm" variant="ghost" disabled={page >= faq.pages} onClick={() => setPage(page + 1)}>
                  {t("common.next")}
                </Button>
              </div>
            )}
          </Card>
        )
      ) : !templates ? (
        <Spinner label={t("common.loading")} />
      ) : templates.length === 0 ? (
        <Empty>{t("kb.empty")}</Empty>
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs text-muted">
              <tr>
                <th className="p-3 font-medium">{t("kb.articleTitle")}</th>
                <th className="p-3 font-medium">{t("kb.language")}</th>
                <th className="p-3 font-medium">{t("kb.category")}</th>
                <th className="p-3 text-right font-medium">{t("kb.usage")}</th>
                <th className="p-3 font-medium">{t("kb.active")}</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {templates.map((tpl) => (
                <tr key={tpl.id} className={clsx("border-t border-border align-top", !tpl.is_active && "opacity-60")}>
                  <td className="p-3">
                    <div className="font-medium">{tpl.title}</div>
                    <div className="line-clamp-2 max-w-xl text-xs text-muted">{tpl.body}</div>
                  </td>
                  <td className="p-3 uppercase">{tpl.language}</td>
                  <td className="p-3">{tpl.category_name ?? "—"}</td>
                  <td className="p-3 text-right tabular-nums">{tpl.usage_count}</td>
                  <td className="p-3">{tpl.is_active ? "✓" : "—"}</td>
                  <td className="whitespace-nowrap p-1 text-right">
                    {canEditTpl(tpl) && (
                      <>
                        <button aria-label={`${t("common.edit")}: ${tpl.title}`} className="inline-grid h-11 w-11 place-items-center rounded-md hover:bg-surface-2" onClick={() => setEditingTpl(tpl)}>
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          aria-label={`${t("common.delete")}: ${tpl.title}`}
                          className="inline-grid h-11 w-11 place-items-center rounded-md text-critical hover:bg-surface-2"
                          onClick={() => api(`/admin/reply-templates/${tpl.id}`, { method: "DELETE" }).then(load).catch(() => {})}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {editing && <FaqEditor slug={editing.slug} startLang={editing.lang} user={user} cats={cats} onClose={() => setEditing(null)} onChanged={load} />}
      {editingTpl && (
        <TemplateEditor
          tpl={editingTpl}
          cats={cats}
          onClose={() => setEditingTpl(null)}
          onSaved={() => {
            setEditingTpl(null);
            setToast(t("common.saved"));
            load();
          }}
        />
      )}
      {toast && <Toast message={toast} onDone={() => setToast("")} />}
    </div>
  );
}

export default function KnowledgeBasePage() {
  return (
    <Guard roles={["agent", "unit_head", "admin"]}>
      <KbView />
    </Guard>
  );
}
