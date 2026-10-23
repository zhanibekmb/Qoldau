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

const WORKFLOWS = ["standard", "approval", "document", "urgent", "triage"].map((w) => ({ value: w, label: w }));
const PRIORITIES = ["Critical", "High", "Medium", "Low"].map((p) => ({ value: p, label: p }));
const ROLES = ["student", "agent", "unit_head", "admin"].map((r) => ({ value: r, label: r }));
const LANGS = ["en", "ru", "kz"].map((l) => ({ value: l, label: l.toUpperCase() }));

function AdminView() {
  const { lang } = useI18n();
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
  const headOpts = () => [
    { value: "", label: "—" },
    ...users.filter((u) => u.role === "unit_head" || u.role === "admin").map((u) => ({ value: u.id, label: String(u.name) })),
  ];

  const ENTITIES: Entity[] = [
    {
      key: "routing-rules",
      label: "Routing rules",
      path: "/admin/routing-rules",
      canDelete: true,
      fields: [
        { key: "category_id", label: "Category", type: "select", options: catOpts },
        { key: "unit_id", label: "Unit", type: "select", options: unitOpts },
        { key: "is_active", label: "Active", type: "bool", default: true },
      ],
    },
    {
      key: "categories",
      label: "Categories",
      path: "/admin/categories",
      canDelete: true,
      fields: [
        { key: "name", label: "Name", type: "text" },
        { key: "unit_id", label: "Default unit", type: "select", options: unitOpts },
        { key: "default_workflow", label: "Workflow", type: "select", options: () => WORKFLOWS, default: "standard" },
        { key: "base_priority_weight", label: "Priority weight (0-60)", type: "number", default: 30 },
        { key: "is_active", label: "Active", type: "bool", default: true },
      ],
    },
    {
      key: "units",
      label: "Units",
      path: "/admin/units",
      canDelete: true,
      fields: [
        { key: "name", label: "Name", type: "text" },
        { key: "email", label: "Email", type: "text", default: "" },
        { key: "head_user_id", label: "Head", type: "select", options: headOpts },
        { key: "working_hours", label: "Working hours", type: "text", default: "Mon-Fri 09:00-18:00" },
        { key: "is_triage", label: "Triage unit", type: "bool", default: false },
      ],
    },
    {
      key: "sla-policies",
      label: "SLA policies",
      path: "/admin/sla-policies",
      fields: [
        { key: "priority", label: "Priority", type: "select", options: () => PRIORITIES },
        { key: "first_response_hours", label: "First response (h)", type: "number" },
        { key: "resolution_hours", label: "Resolution (h)", type: "number" },
        { key: "use_working_hours", label: "Working hours only", type: "bool", default: false },
      ],
    },
    {
      key: "keywords",
      label: "Urgency keywords",
      path: "/admin/keywords",
      canDelete: true,
      fields: [
        { key: "keyword", label: "Keyword", type: "text" },
        { key: "weight", label: "Weight (-30..60)", type: "number", default: 10 },
        { key: "is_critical", label: "Forces Critical", type: "bool", default: false },
        { key: "language", label: "Language", type: "select", options: () => LANGS, default: "en" },
      ],
    },
    {
      key: "users",
      label: "Users & roles",
      path: "/admin/users",
      fields: [
        { key: "name", label: "Name", type: "text" },
        { key: "email", label: "Email", type: "text" },
        { key: "role", label: "Role", type: "select", options: () => ROLES, default: "student" },
        { key: "unit_id", label: "Unit", type: "select", options: unitOpts },
        { key: "language", label: "Language", type: "select", options: () => LANGS, default: "en" },
        { key: "is_active", label: "Active", type: "bool", default: true },
        { key: "password", label: "Password (leave empty to keep)", type: "password", hideInTable: true },
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
      setError(err instanceof ApiError ? err.message : "Failed");
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
      setError(err instanceof ApiError ? err.message : "Failed");
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
      <h1 className="text-2xl font-bold">Configuration</h1>
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1" role="tablist">
        {[...ENTITIES.map((e) => [e.key, e.label]), ["audit", "Audit log"]].map(([k, l]) => (
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
                  <th className="p-3 font-medium">When</th>
                  <th className="p-3 font-medium">Who</th>
                  <th className="p-3 font-medium">Action</th>
                  <th className="p-3 font-medium">Entity</th>
                  <th className="p-3 font-medium">Change (old → new)</th>
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
                <Plus className="h-4 w-4" /> Add
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
                        <button aria-label="Edit" className="inline-grid h-11 w-11 place-items-center rounded-lg hover:bg-surface-2" onClick={() => open(r)}>
                          <Pencil className="h-4 w-4" />
                        </button>
                        {entity.canDelete && (
                          <button aria-label="Delete" className="inline-grid h-11 w-11 place-items-center rounded-lg text-critical hover:bg-surface-2" onClick={() => remove(r)}>
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

      <Modal open={!!editing} onClose={() => setEditing(null)} title={editing === "new" ? `Add: ${entity?.label}` : `Edit: ${entity?.label}`}>
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
                      step="any"
                      value={String(form[f.key] ?? "")}
                      onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                    />
                  )}
                </>
              )}
            </div>
          ))}
          <FieldError>{error}</FieldError>
          <div className="flex gap-2">
            <Button type="submit" loading={busy}>
              Save
            </Button>
            <Button type="button" variant="ghost" onClick={() => setEditing(null)}>
              Cancel
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
