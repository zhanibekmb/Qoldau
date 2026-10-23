"use client";

import { Cpu, UserCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { AgentMeta, CategoryMeta, Priority, RequestDetail, UnitMeta, User } from "@/lib/types";
import { Button, Card, FieldError, Input, Label, Select, Textarea } from "./ui";

/** Highlight the words that drove the AI decision inside the request text. */
export function Highlighted({ text, keywords }: { text: string; keywords: string[] }) {
  const words = keywords.flatMap((k) => k.split(" ")).filter((w) => w.length > 2);
  if (!words.length) return <>{text}</>;
  const re = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "giu");
  return (
    <>
      {text.split(re).map((part, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="rounded bg-yellow-300/60 px-0.5 text-inherit dark:bg-yellow-500/40">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

/** AI Decision panel + override (US9). Staff only; never rendered for students. */
export function AiPanel({ req, onChange }: { req: RequestDetail; onChange: (r: RequestDetail) => void }) {
  const ai = req.ai!;
  const [cats, setCats] = useState<CategoryMeta[]>([]);
  const [units, setUnits] = useState<UnitMeta[]>([]);
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("");
  const [unit, setUnit] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pct = Math.round((ai.confidence ?? 0) * 100);

  useEffect(() => {
    api<CategoryMeta[]>("/meta/categories").then(setCats).catch(() => {});
    api<UnitMeta[]>("/meta/units").then(setUnits).catch(() => {});
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!category && !priority && !unit) return setError("Choose what to correct");
    if (reason.trim().length < 3) return setError("A short reason is required");
    setBusy(true);
    try {
      const r = await api<RequestDetail>(`/requests/${req.id}/override`, {
        method: "POST",
        json: {
          category_id: category ? Number(category) : null,
          priority: priority || null,
          unit_id: unit ? Number(unit) : null,
          reason: reason.trim(),
        },
      });
      onChange(r);
      setCategory("");
      setPriority("");
      setUnit("");
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <h2 className="mb-3 flex items-center gap-2 font-semibold">
        <Cpu className="h-5 w-5 text-primary" aria-hidden /> AI Decision
      </h2>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted">Category</dt>
        <dd className="font-medium">{ai.predicted_category?.name ?? "—"}</dd>
        <dt className="text-muted">Urgency</dt>
        <dd className="font-medium">
          {ai.predicted_priority} ({req.priority_score}/100)
        </dd>
        <dt className="text-muted">Unit</dt>
        <dd className="font-medium">{ai.predicted_unit?.name ?? "Triage"}</dd>
        {ai.student_category && (
          <>
            <dt className="text-muted">Student chose</dt>
            <dd>{ai.student_category.name}</dd>
          </>
        )}
      </dl>
      <div className="mt-3">
        <div className="mb-1 flex justify-between text-xs">
          <span className="text-muted">Confidence</span>
          <span className="font-semibold">{pct}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="AI confidence">
          <div className={pct < 60 ? "h-full bg-warn" : "h-full bg-ok"} style={{ width: `${pct}%` }} />
        </div>
      </div>
      {ai.alternatives.length > 0 && (
        <div className="mt-3">
          <div className="mb-1 text-xs text-muted">Top-3 alternatives</div>
          <ul className="space-y-1 text-sm">
            {ai.alternatives.map((a) => (
              <li key={a.category} className="flex justify-between gap-2">
                <span>{a.category}</span>
                <span className="tabular-nums text-muted">{Math.round(a.confidence * 100)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {ai.keywords.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {ai.keywords.map((k) => (
            <span key={k} className="rounded bg-yellow-300/50 px-1.5 py-0.5 text-xs dark:bg-yellow-500/30">
              {k}
            </span>
          ))}
        </div>
      )}
      {ai.priority_reasons.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="min-h-11 cursor-pointer py-2 text-muted">Why this urgency?</summary>
          <ul className="list-disc pl-5 text-xs text-muted">
            {ai.priority_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </details>
      )}
      {ai.model_version && <p className="mt-2 text-xs text-muted">Model {ai.model_version}</p>}

      <form onSubmit={save} className="mt-4 space-y-2 border-t border-border pt-4">
        <h3 className="text-sm font-semibold">Correct the AI decision</h3>
        <Select aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Category: keep</option>
          {cats.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select aria-label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="">Urgency: keep</option>
          {(["Critical", "High", "Medium", "Low"] as Priority[]).map((p) => (
            <option key={p}>{p}</option>
          ))}
        </Select>
        <Select aria-label="Unit" value={unit} onChange={(e) => setUnit(e.target.value)}>
          <option value="">Unit: keep</option>
          {units.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </Select>
        <Input aria-label="Reason" placeholder="Reason (required)" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
        <FieldError>{error}</FieldError>
        <Button type="submit" variant="secondary" loading={busy} className="w-full">
          Save correction
        </Button>
      </form>
    </Card>
  );
}

const ACTION_LABEL: Record<string, string> = {
  "In Progress": "Start work",
  "Waiting for Student": "Ask student",
  Resolved: "Resolve",
  Closed: "Close",
  Routed: "Back to queue",
  Reopened: "Reopen",
};

/** Status actions, assignment and workflow steps for agents. */
export function StaffActions({ req, viewer, onChange }: { req: RequestDetail; viewer: User; onChange: (r: RequestDetail) => void }) {
  const [agents, setAgents] = useState<AgentMeta[]>([]);
  const [target, setTarget] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!req.unit) return;
    api<AgentMeta[]>(`/meta/agents?unit_id=${req.unit.id}`).then(setAgents).catch(() => {});
  }, [req.unit]);

  const actions = req.allowed_transitions.filter((s) => s in ACTION_LABEL && s !== "Closed" && s !== "Reopened" && s !== "Routed");

  async function run(path: string, json: unknown, method = "POST") {
    setBusy(true);
    setError("");
    try {
      onChange(await api<RequestDetail>(path, { method, json }));
      setTarget(null);
      setMessage("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  const step = req.workflow_steps[req.workflow_step];
  const nextStep = req.workflow_steps[req.workflow_step + 1];

  return (
    <Card className="space-y-4">
      <div>
        <h2 className="mb-2 font-semibold">Actions</h2>
        {actions.length === 0 && <p className="text-sm text-muted">No status change available.</p>}
        <div className="flex flex-wrap gap-2">
          {actions.map((s) => (
            <Button key={s} size="sm" variant={s === "Resolved" ? "primary" : "secondary"} onClick={() => setTarget(s)}>
              {ACTION_LABEL[s]}
            </Button>
          ))}
        </div>
        {target && (
          <form
            className="mt-3 space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              run(`/requests/${req.id}/status`, { status: target, message: message.trim() || null }, "PATCH");
            }}
          >
            <Label htmlFor="status-msg">Message to student {target === "Waiting for Student" ? "(your question)" : "(optional)"}</Label>
            <Textarea id="status-msg" rows={3} value={message} onChange={(e) => setMessage(e.target.value)} maxLength={2000} />
            <div className="flex gap-2">
              <Button type="submit" size="sm" loading={busy} disabled={target === "Waiting for Student" && !message.trim()}>
                Confirm: {target}
              </Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => setTarget(null)}>
                Cancel
              </Button>
            </div>
          </form>
        )}
      </div>

      {req.workflow_steps.length > 0 && (
        <div>
          <h3 className="mb-1 text-sm font-semibold">Workflow ({req.workflow})</h3>
          <p className="text-sm text-muted">
            Current step: <strong className="text-text">{step}</strong>
          </p>
          {nextStep && (
            <Button size="sm" variant="secondary" className="mt-2" loading={busy} onClick={() => run(`/requests/${req.id}/step`, {})}>
              Move to “{nextStep}”
            </Button>
          )}
        </div>
      )}

      {req.status !== "Needs Review" && req.unit && (
        <div>
          <h3 className="mb-1 text-sm font-semibold">Assignee</h3>
          <div className="flex gap-2">
            <Select
              aria-label="Assignee"
              value={req.assignee?.id ?? ""}
              onChange={(e) => e.target.value && run(`/requests/${req.id}/assign`, { assignee_id: Number(e.target.value) })}
            >
              <option value="">Unassigned (unit queue)</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} · {a.open_tickets} open{a.online ? " · online" : ""}
                </option>
              ))}
            </Select>
            {viewer.unit_id === req.unit.id && req.assignee?.id !== viewer.id && (
              <Button size="sm" variant="secondary" aria-label="Assign to me" onClick={() => run(`/requests/${req.id}/assign`, { assignee_id: viewer.id })}>
                <UserCheck className="h-4 w-4" /> Me
              </Button>
            )}
          </div>
        </div>
      )}
      <FieldError>{error}</FieldError>
    </Card>
  );
}
