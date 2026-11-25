"use client";

import clsx from "clsx";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Guard } from "@/components/Guard";
import { Button, Card, FieldError, Input, Label, Modal, Select, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

type Row = Record<string, unknown> & { id: number };
type Option = { value: string | number; label: string };
interface Field {
  key: string;
  label: string;
  type: "text" | "number" | "bool" | "select" | "password";
  options?: () => Option[];
  default?: unknown;
  hideInTable?: boolean;
}
interface Entity {
  key: string;
  label: string;
  path: string;
  fields: Field[];
  canDelete?: boolean;
}

const COPY = {
  en: {
    routingRules: "Routing rules", categories: "Categories", units: "Units", slaPolicies: "SLA policies",
    urgencyKeywords: "Urgency keywords", usersRoles: "Users & roles", auditLog: "Audit log",
    category: "Category", unit: "Unit", active: "Active", name: "Name", defaultUnit: "Default unit",
    workflow: "Workflow", priorityWeight: "Priority weight (0–60)", email: "Email", head: "Head",
    workingHours: "Working hours", triageUnit: "Triage unit", priority: "Priority",
    firstResponse: "First response (h)", resolution: "Resolution (h)", workingHoursOnly: "Working hours only",
    keyword: "Keyword", weight: "Weight (−30 to 60)", forcesCritical: "Forces Critical",
    language: "Language", role: "Role", passwordKeep: "Temporary password (12+ characters)",
    passwordHint: "Required for new accounts. Leave empty when editing to keep the current password.",
    when: "When", who: "Who", action: "Action", entity: "Entity", change: "Change (old → new)",
    add: "Add", edit: "Edit", delete: "Delete", save: "Save", cancel: "Cancel",
    workflows: { standard: "Standard", approval: "Approval", document: "Document", urgent: "Urgent", triage: "Triage" },
    roles: { student: "Student", agent: "Agent", unit_head: "Unit head", admin: "Admin" },
  },
  ru: {
    routingRules: "Правила маршрутизации", categories: "Категории", units: "Подразделения", slaPolicies: "Правила SLA",
    urgencyKeywords: "Ключевые слова срочности", usersRoles: "Пользователи и роли", auditLog: "Журнал изменений",
    category: "Категория", unit: "Подразделение", active: "Активно", name: "Название", defaultUnit: "Подразделение по умолчанию",
    workflow: "Процесс", priorityWeight: "Вес приоритета (0–60)", email: "Эл. почта", head: "Руководитель",
    workingHours: "Рабочие часы", triageUnit: "Подразделение первичной обработки", priority: "Приоритет",
    firstResponse: "Первый ответ (ч)", resolution: "Решение (ч)", workingHoursOnly: "Только рабочие часы",
    keyword: "Ключевое слово", weight: "Вес (от −30 до 60)", forcesCritical: "Принудительно критический",
    language: "Язык", role: "Роль", passwordKeep: "Временный пароль (от 12 символов)",
    passwordHint: "Обязателен для нового аккаунта. При редактировании пустое поле сохраняет текущий пароль.",
    when: "Когда", who: "Кто", action: "Действие", entity: "Объект", change: "Изменение (было → стало)",
    add: "Добавить", edit: "Изменить", delete: "Удалить", save: "Сохранить", cancel: "Отмена",
    workflows: { standard: "Стандартный", approval: "Согласование", document: "Документ", urgent: "Срочный", triage: "Первичная обработка" },
    roles: { student: "Студент", agent: "Сотрудник", unit_head: "Руководитель", admin: "Администратор" },
  },
  kz: {
    routingRules: "Бағыттау ережелері", categories: "Санаттар", units: "Бөлімдер", slaPolicies: "SLA ережелері",
    urgencyKeywords: "Шұғылдық кілт сөздері", usersRoles: "Пайдаланушылар мен рөлдер", auditLog: "Өзгерістер журналы",
    category: "Санат", unit: "Бөлім", active: "Белсенді", name: "Атауы", defaultUnit: "Әдепкі бөлім",
    workflow: "Үдеріс", priorityWeight: "Басымдық салмағы (0–60)", email: "Эл. пошта", head: "Басшы",
    workingHours: "Жұмыс уақыты", triageUnit: "Алғашқы қарау бөлімі", priority: "Басымдық",
    firstResponse: "Алғашқы жауап (сағ)", resolution: "Шешу (сағ)", workingHoursOnly: "Тек жұмыс уақыты",
    keyword: "Кілт сөз", weight: "Салмақ (−30–60)", forcesCritical: "Міндетті түрде шұғыл",
    language: "Тіл", role: "Рөл", passwordKeep: "Уақытша құпиясөз (кемінде 12 таңба)",
    passwordHint: "Жаңа аккаунтқа міндетті. Өңдеу кезінде бос қалдырсаңыз, құпиясөз сақталады.",
    when: "Қашан", who: "Кім", action: "Әрекет", entity: "Нысан", change: "Өзгеріс (бұрын → кейін)",
    add: "Қосу", edit: "Өңдеу", delete: "Жою", save: "Сақтау", cancel: "Бас тарту",
    workflows: { standard: "Стандартты", approval: "Бекіту", document: "Құжат", urgent: "Шұғыл", triage: "Алғашқы қарау" },
    roles: { student: "Студент", agent: "Қызметкер", unit_head: "Бөлім басшысы", admin: "Әкімші" },
  },
} as const;

const WORKFLOWS = ["standard", "approval", "document", "urgent", "triage"] as const;
const PRIORITIES = ["Critical", "High", "Medium", "Low"] as const;
const ROLES = ["student", "agent", "unit_head", "admin"] as const;
const LANGS = ["en", "ru", "kz"].map((l) => ({ value: l, label: l.toUpperCase() }));

function AdminView() {
  const { lang, t } = useI18n();
  const c = COPY[lang];
  const [units, setUnits] = useState<Row[]>([]);
  const [cats, setCats] = useState<Row[]>([]);
  const [users, setUsers] = useState<Row[]>([]);
  const [tab, setTab] = useState("routing-rules");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [editing, setEditing] = useState<Row | "new" | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [audit, setAudit] = useState<Row[] | null>(null);

  const unitOpts = () => [{ value: "", label: "—" }, ...units.map((u) => ({ value: u.id, label: String(u.name) }))];
  const catOpts = () => cats.map((c) => ({ value: c.id, label: String(c.name) }));
  const workflowOpts = () => WORKFLOWS.map((w) => ({ value: w, label: c.workflows[w] }));
  const priorityOpts = () => PRIORITIES.map((p) => ({ value: p, label: t(`prio.${p}`) }));
  const roleOpts = () => ROLES.map((r) => ({ value: r, label: c.roles[r] }));
  const headOpts = () => [
    { value: "", label: "—" },
    ...users.filter((u) => u.role === "unit_head" || u.role === "admin").map((u) => ({ value: u.id, label: String(u.name) })),
  ];

  const ENTITIES: Entity[] = [
    {
      key: "routing-rules",
      label: c.routingRules,
      path: "/admin/routing-rules",
      canDelete: true,
      fields: [
        { key: "category_id", label: c.category, type: "select", options: catOpts },
        { key: "unit_id", label: c.unit, type: "select", options: unitOpts },
        { key: "is_active", label: c.active, type: "bool", default: true },
      ],
    },
    {
      key: "categories",
      label: c.categories,
      path: "/admin/categories",
      canDelete: true,
      fields: [
        { key: "name", label: c.name, type: "text" },
        { key: "unit_id", label: c.defaultUnit, type: "select", options: unitOpts },
        { key: "default_workflow", label: c.workflow, type: "select", options: workflowOpts, default: "standard" },
        { key: "base_priority_weight", label: c.priorityWeight, type: "number", default: 30 },
        { key: "is_active", label: c.active, type: "bool", default: true },
      ],
    },
    {
      key: "units",
      label: c.units,
      path: "/admin/units",
      canDelete: true,
      fields: [
        { key: "name", label: c.name, type: "text" },
        { key: "email", label: c.email, type: "text", default: "" },
        { key: "head_user_id", label: c.head, type: "select", options: headOpts },
        { key: "working_hours", label: c.workingHours, type: "text", default: "Mon-Fri 09:00-18:00" },
        { key: "is_triage", label: c.triageUnit, type: "bool", default: false },
      ],
    },
    {
      key: "sla-policies",
      label: c.slaPolicies,
      path: "/admin/sla-policies",
      fields: [
        { key: "priority", label: c.priority, type: "select", options: priorityOpts },
        { key: "first_response_hours", label: c.firstResponse, type: "number" },
        { key: "resolution_hours", label: c.resolution, type: "number" },
        { key: "use_working_hours", label: c.workingHoursOnly, type: "bool", default: false },
      ],
    },
    {
      key: "keywords",
      label: c.urgencyKeywords,
      path: "/admin/keywords",
      canDelete: true,
      fields: [
        { key: "keyword", label: c.keyword, type: "text" },
        { key: "weight", label: c.weight, type: "number", default: 10 },
        { key: "is_critical", label: c.forcesCritical, type: "bool", default: false },
        { key: "language", label: c.language, type: "select", options: () => LANGS, default: "en" },
      ],
    },
    {
      key: "users",
      label: c.usersRoles,
      path: "/admin/users",
      fields: [
        { key: "name", label: c.name, type: "text" },
        { key: "email", label: c.email, type: "text" },
        { key: "role", label: c.role, type: "select", options: roleOpts, default: "student" },
        { key: "unit_id", label: c.unit, type: "select", options: unitOpts },
        { key: "language", label: c.language, type: "select", options: () => LANGS, default: "en" },
        { key: "is_active", label: c.active, type: "bool", default: true },
        { key: "password", label: c.passwordKeep, type: "password", hideInTable: true },
      ],
    },
  ];
  const entity = ENTITIES.find((e) => e.key === tab);

  const loadRefs = useCallback(() => {
    api<Row[]>("/admin/units").then(setUnits).catch(() => {});
    api<Row[]>("/admin/categories").then(setCats).catch(() => {});
    api<Row[]>("/admin/users").then(setUsers).catch(() => {});
  }, []);

  const load = useCallback(() => {
    if (tab === "audit") {
      api<Row[]>("/admin/audit-log").then(setAudit).catch(() => {});
      return;
    }
    const e = ["routing-rules", "categories", "units", "sla-policies", "keywords", "users"].includes(tab) ? tab : "routing-rules";
    setRows(null);
    api<Row[]>(`/admin/${e}`).then(setRows).catch(() => setRows([]));
  }, [tab]);

  useEffect(loadRefs, [loadRefs]);
  useEffect(load, [load]);

  function open(row: Row | "new") {
    if (!entity) return;
    setError("");
    const init: Record<string, unknown> = {};
    for (const f of entity.fields) init[f.key] = row === "new" ? (f.default ?? "") : (row[f.key] ?? (f.type === "password" ? "" : ""));
    setForm(init);
    setEditing(row);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!entity || !editing) return;
    setBusy(true);
    setError("");
    const body: Record<string, unknown> = {};
    for (const f of entity.fields) {
      let v = form[f.key];
      if (f.type === "number") v = v === "" ? null : Number(v);
      if (f.type === "select" && (f.key.endsWith("_id") || f.key === "head_user_id")) v = v === "" || v === null ? null : Number(v);
      if (f.type === "password" && !v) v = null;
      body[f.key] = v;
    }
    try {
      if (editing === "new") await api(entity.path, { method: "POST", json: body });
      else await api(`${entity.path}/${editing.id}`, { method: "PUT", json: body });
      setEditing(null);
      load();
      loadRefs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  async function remove(row: Row) {
    if (!entity) return;
    try {
      await api(`${entity.path}/${row.id}`, { method: "DELETE" });
      load();
      loadRefs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    }
  }

  const display = (f: Field, row: Row) => {
    const v = row[f.key];
    if (f.type === "bool") return v ? "✓" : "—";
    if (f.type === "select" && f.options) {
      if (f.key === "category_id" && row.category_name) return String(row.category_name);
      if (f.key === "unit_id" && row.unit_name) return String(row.unit_name);
      return f.options().find((o) => String(o.value) === String(v))?.label ?? (v === null ? "—" : String(v));
    }
    return v === null || v === undefined || v === "" ? "—" : String(v);
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("nav.admin")}</h1>
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1" role="tablist">
        {[...ENTITIES.map((e) => [e.key, e.label]), ["audit", c.auditLog]].map(([k, l]) => (
          <Button key={k} role="tab" aria-selected={tab === k} size="sm" variant={tab === k ? "primary" : "secondary"} onClick={() => setTab(k)} className="shrink-0">
            {l}
          </Button>
        ))}
      </div>
      <FieldError>{!editing && error}</FieldError>

      {tab === "audit" ? (
        <Card className="overflow-x-auto p-0">
          {!audit ? (
            <Spinner />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-left text-xs text-muted">
                <tr>
                  <th className="p-3 font-medium">{c.when}</th>
                  <th className="p-3 font-medium">{c.who}</th>
                  <th className="p-3 font-medium">{c.action}</th>
                  <th className="p-3 font-medium">{c.entity}</th>
                  <th className="p-3 font-medium">{c.change}</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((a) => {
                  const oldV = (a.old ?? {}) as Record<string, unknown>;
                  const newV = (a.new ?? {}) as Record<string, unknown>;
                  const keys = Array.from(new Set([...Object.keys(oldV), ...Object.keys(newV)])).filter(
                    (k) => k !== "id" && JSON.stringify(oldV[k]) !== JSON.stringify(newV[k]),
                  );
                  return (
                    <tr key={a.id} className="border-t border-border align-top">
                      <td className="whitespace-nowrap p-3">{fmtDate(String(a.created_at), lang)}</td>
                      <td className="p-3">{(a.actor as { name: string } | null)?.name ?? "—"}</td>
                      <td className="p-3">{String(a.action)}</td>
                      <td className="p-3">
                        {String(a.entity)} #{String(a.entity_id)}
                      </td>
                      <td className="p-3 font-mono text-xs">
                        {keys.slice(0, 6).map((k) => (
                          <div key={k}>
                            {k}: {JSON.stringify(oldV[k] ?? null)} → {JSON.stringify(newV[k] ?? null)}
                          </div>
                        ))}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
      ) : (
        entity && (
          <Card className="overflow-x-auto p-0">
            <div className="flex items-center justify-between p-3">
              <h2 className="font-semibold">{entity.label}</h2>
              <Button size="sm" onClick={() => open("new")}>
                <Plus className="h-4 w-4" /> {c.add}
              </Button>
            </div>
            {!rows ? (
              <Spinner />
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-surface-2 text-left text-xs text-muted">
                  <tr>
                    {entity.fields
                      .filter((f) => !f.hideInTable)
                      .map((f) => (
                        <th key={f.key} className="p-3 font-medium">
                          {f.label}
                        </th>
                      ))}
                    <th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id} className={clsx("border-t border-border", r.is_active === false && "opacity-60")}>
                      {entity.fields
                        .filter((f) => !f.hideInTable)
                        .map((f) => (
                          <td key={f.key} className="p-3">
                            {display(f, r)}
                          </td>
                        ))}
                      <td className="whitespace-nowrap p-1 text-right">
                        <button aria-label={c.edit} className="inline-grid h-11 w-11 place-items-center rounded-lg hover:bg-surface-2" onClick={() => open(r)}>
                          <Pencil className="h-4 w-4" />
                        </button>
                        {entity.canDelete && (
                          <button aria-label={c.delete} className="inline-grid h-11 w-11 place-items-center rounded-lg text-critical hover:bg-surface-2" onClick={() => remove(r)}>
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        )
      )}

      <Modal open={!!editing} onClose={() => setEditing(null)} title={editing === "new" ? `${c.add}: ${entity?.label}` : `${c.edit}: ${entity?.label}`}>
        <form onSubmit={save} className="space-y-3">
          {entity?.fields.map((f) => (
            <div key={f.key}>
              {f.type === "bool" ? (
                <label className="flex min-h-11 items-center gap-2 text-sm">
                  <input type="checkbox" className="h-5 w-5" checked={!!form[f.key]} onChange={(e) => setForm({ ...form, [f.key]: e.target.checked })} />
                  {f.label}
                </label>
              ) : (
                <>
                  <Label htmlFor={`f-${f.key}`}>{f.label}</Label>
                  {f.type === "select" ? (
                    <Select id={`f-${f.key}`} value={String(form[f.key] ?? "")} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}>
                      {f.options?.().map((o) => (
                        <option key={String(o.value)} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <Input
                      id={`f-${f.key}`}
                      type={f.type === "number" ? "number" : f.type === "password" ? "password" : "text"}
                      autoComplete={f.type === "password" ? "new-password" : undefined}
                      minLength={f.type === "password" ? 12 : undefined}
                      maxLength={f.type === "password" ? 72 : undefined}
                      aria-describedby={f.type === "password" ? "temporary-password-hint" : undefined}
                      step="any"
                      value={String(form[f.key] ?? "")}
                      onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                    />
                  )}
                  {f.type === "password" && <p id="temporary-password-hint" className="mt-1 text-xs text-muted">{c.passwordHint}</p>}
                </>
              )}
            </div>
          ))}
          <FieldError>{error}</FieldError>
          <div className="flex gap-2">
            <Button type="submit" loading={busy}>
              {c.save}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setEditing(null)}>
              {c.cancel}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

export default function AdminPage() {
  return (
    <Guard roles={["admin"]}>
      <AdminView />
    </Guard>
  );
}
