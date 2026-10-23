"use client";

import clsx from "clsx";
import { Cpu, Loader2, RotateCcw, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Guard } from "@/components/Guard";
import { Badge, Button, Card, Empty, FieldError, Modal, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { ModelVersion, TrainingRun } from "@/lib/types";

interface Overview {
  active: Partial<Record<"classifier" | "priority", ModelVersion>>;
  feedback_since_last_training: number;
  threshold: number;
  loaded_version: string;
  running_run_id: number | null;
  last_run: TrainingRun | null;
}

const STATUS_CLS = { active: "bg-ok/12 text-ok", candidate: "bg-primary-soft text-primary", archived: "bg-surface-2 text-muted" };
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const axis = { stroke: "var(--muted)", fontSize: 12, tickLine: false, axisLine: false } as const;

function ActiveCard({ type, m }: { type: "classifier" | "priority"; m?: ModelVersion }) {
  const { t, lang } = useI18n();
  return (
    <Card>
      <div className="flex items-center gap-2 text-sm text-muted">
        <Cpu className="h-4 w-4" aria-hidden /> {t(type === "classifier" ? "ml.classifier" : "ml.priority")}
      </div>
      {m ? (
        <>
          <div className="mt-1 text-3xl font-bold">{m.version}</div>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted">{t("ml.accuracy")}</dt>
            <dd className="text-right font-semibold tabular-nums">{pct(m.accuracy)}</dd>
            <dt className="text-muted">{t("ml.f1")}</dt>
            <dd className="text-right font-semibold tabular-nums">{m.macro_f1.toFixed(3)}</dd>
            <dt className="text-muted">{t("ml.trainSize")}</dt>
            <dd className="text-right tabular-nums">{m.train_size}</dd>
            <dt className="text-muted">{t("ml.trained")}</dt>
            <dd className="text-right">{fmtDate(m.trained_at, lang, false)}</dd>
          </dl>
          {type === "priority" && <p className="mt-2 text-xs text-muted">{t("ml.priorityHint")}</p>}
        </>
      ) : (
        <p className="mt-2 text-sm text-muted">{t("ml.noModels")}</p>
      )}
    </Card>
  );
}

/** Per-class F1 bars + confusion-matrix heatmap for one version. */
function ModelDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const { t } = useI18n();
  const [m, setM] = useState<ModelVersion | null>(null);
  useEffect(() => {
    api<ModelVersion>(`/ai/models/${id}`).then(setM).catch(() => {});
  }, [id]);
  const f1 = Object.entries(m?.metrics?.per_class_f1 ?? {}).sort((a, b) => a[1] - b[1]);
  const cm = m?.metrics?.confusion_matrix;
  const maxCell = cm ? Math.max(1, ...cm.matrix.flat()) : 1;

  return (
    <Modal open onClose={onClose} size="xl" title={m ? `${m.version} · ${t(m.model_type === "classifier" ? "ml.classifier" : "ml.priority")}` : t("common.details")}>
      {!m ? (
        <Spinner />
      ) : (
        <div className="space-y-6">
          <p className="text-sm text-muted">
            {t("ml.accuracy")} {pct(m.accuracy)} · {t("ml.f1")} {m.macro_f1.toFixed(3)} · {t("ml.trainSize")} {m.train_size} · {t("ml.feedback")} {m.feedback_count}
          </p>
          {f1.length > 0 && (
            <section>
              <h3 className="mb-3 font-semibold">{t("ml.perClass")}</h3>
              <ul className="space-y-2">
                {f1.map(([label, v]) => (
                  <li key={label} className="grid grid-cols-[minmax(0,12rem)_1fr_auto] items-center gap-3 text-sm" title={`${label}: F1 ${v.toFixed(3)}`}>
                    <span className="truncate">{label}</span>
                    <span className="h-2.5 rounded-r bg-surface-2">
                      <span className="block h-full rounded-r" style={{ width: `${v * 100}%`, background: "var(--series-1)" }} />
                    </span>
                    <span className="w-12 text-right font-semibold tabular-nums">{v.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {cm && (
            <section>
              <h3 className="font-semibold">{t("ml.confusion")}</h3>
              <p className="mb-3 text-sm text-muted">{t("ml.confusionHint")}</p>
              <div className="overflow-x-auto">
                <table className="border-separate border-spacing-0.5 text-xs">
                  <thead>
                    <tr>
                      <th />
                      {cm.labels.map((l) => (
                        <th key={l} scope="col" className="h-44 w-9 align-bottom font-medium text-muted">
                          <span className="inline-block max-h-44 overflow-hidden whitespace-nowrap [writing-mode:vertical-rl] rotate-180" title={l}>
                            {l}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cm.matrix.map((row, i) => (
                      <tr key={cm.labels[i]}>
                        <th scope="row" className="max-w-[11rem] truncate pr-2 text-left font-medium text-muted" title={cm.labels[i]}>
                          {cm.labels[i]}
                        </th>
                        {row.map((v, j) => {
                          const share = v / maxCell;
                          return (
                            <td
                              key={j}
                              title={`${cm.labels[i]} → ${cm.labels[j]}: ${v}`}
                              className={clsx("h-9 w-9 rounded-sm text-center tabular-nums", share > 0.5 ? "text-white" : "text-text", i === j && v > 0 && "ring-1 ring-inset ring-text/20")}
                              style={{ background: v ? `color-mix(in srgb, var(--series-1) ${Math.round(15 + share * 85)}%, var(--surface))` : "var(--surface-2)" }}
                            >
                              {v || ""}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </Modal>
  );
}

function ModelsView() {
  const { t, lang } = useI18n();
  const [ov, setOv] = useState<Overview | null>(null);
  const [models, setModels] = useState<ModelVersion[] | null>(null);
  const [type, setType] = useState<"classifier" | "priority">("classifier");
  const [confirmRetrain, setConfirmRetrain] = useState(false);
  const [force, setForce] = useState(false);
  const [run, setRun] = useState<TrainingRun | null>(null);
  const [switching, setSwitching] = useState<{ m: ModelVersion; action: "activate" | "rollback" } | null>(null);
  const [detail, setDetail] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Overview>("/ai/models/overview")
      .then((o) => {
        setOv(o);
        if (o.last_run) setRun((r) => r ?? o.last_run);
      })
      .catch(() => {});
    api<ModelVersion[]>("/ai/models").then(setModels).catch(() => setModels([]));
  }, []);
  useEffect(load, [load]);

  // Live status and logs of the current training run.
  const running = run && (run.status === "queued" || run.status === "running");
  useEffect(() => {
    if (!running || !run) return;
    const id = setInterval(() => {
      api<TrainingRun>(`/ai/training-runs/${run.id}`)
        .then((r) => {
          setRun(r);
          if (r.status === "done" || r.status === "failed") load();
        })
        .catch(() => {});
    }, 1500);
    return () => clearInterval(id);
  }, [running, run, load]);

  async function retrain() {
    setBusy(true);
    setError("");
    try {
      setRun(await api<TrainingRun>("/ai/retrain", { method: "POST", json: { force } }));
      setConfirmRetrain(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  async function doSwitch() {
    if (!switching) return;
    setBusy(true);
    setError("");
    try {
      await api(`/ai/models/${switching.m.id}/${switching.action}`, { method: "POST" });
      setSwitching(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  if (!ov || !models) return <Spinner label={t("common.loading")} />;
  const list = models.filter((m) => m.model_type === type);
  const history = [...models.filter((m) => m.model_type === "classifier")].reverse().map((m) => ({ version: m.version, accuracy: +(m.accuracy * 100).toFixed(1) }));
  const progress = Math.min(1, ov.feedback_since_last_training / ov.threshold);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("ml.title")}</h1>
          <p className="text-sm text-muted">{t("ml.loaded", { v: ov.loaded_version })}</p>
        </div>
        <Button onClick={() => { setError(""); setConfirmRetrain(true); }} disabled={!!running}>
          <Zap className="h-4 w-4" aria-hidden /> {t("ml.retrain")}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <ActiveCard type="classifier" m={ov.active.classifier} />
        <ActiveCard type="priority" m={ov.active.priority} />
        <Card>
          <div className="text-sm text-muted">{t("ml.since")}</div>
          <div className="mt-1 text-3xl font-bold tabular-nums">
            {ov.feedback_since_last_training} <span className="text-lg font-normal text-muted">/ {ov.threshold}</span>
          </div>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={ov.feedback_since_last_training} aria-valuemin={0} aria-valuemax={ov.threshold} aria-label={t("ml.since")}>
            <div className="h-full rounded-full" style={{ width: `${progress * 100}%`, background: "var(--series-1)" }} />
          </div>
          <p className="mt-2 text-xs text-muted">{t("ml.sinceHint", { n: ov.threshold })}</p>
        </Card>
      </div>

      {run && (
        <Card aria-live="polite">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h2 className="font-semibold">{t("ml.run", { id: run.id })}</h2>
            <Badge className={run.status === "failed" ? "bg-critical/12 text-critical" : run.status === "done" ? "bg-ok/12 text-ok" : "bg-primary-soft text-primary"}>
              {running && <Loader2 className="h-3 w-3 animate-spin" aria-hidden />}
              {t(`rep.st.${run.status}`)}
            </Badge>
            <span className="text-sm text-muted">{fmtDate(run.created_at, lang)}</span>
          </div>
          <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-md bg-surface-2 p-3 font-mono text-xs leading-relaxed">{run.logs || "…"}</pre>
          {run.error && <FieldError>{run.error}</FieldError>}
        </Card>
      )}

      <Card className="overflow-x-auto p-0">
        <div className="flex flex-wrap items-center justify-between gap-2 p-3">
          <h2 className="font-semibold">{t("ml.versions")}</h2>
          <div role="tablist" className="flex gap-2">
            {(["classifier", "priority"] as const).map((k) => (
              <Button key={k} role="tab" aria-selected={type === k} size="sm" variant={type === k ? "primary" : "secondary"} onClick={() => setType(k)}>
                {t(k === "classifier" ? "ml.classifier" : "ml.priority")}
              </Button>
            ))}
          </div>
        </div>
        {list.length === 0 ? (
          <div className="p-3">
            <Empty>{t("ml.noModels")}</Empty>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-surface-2 text-left text-xs text-muted">
              <tr>
                <th className="p-3 font-medium">{t("ml.version")}</th>
                <th className="p-3 font-medium">{t("kb.status")}</th>
                <th className="p-3 text-right font-medium">{t("ml.accuracy")}</th>
                <th className="p-3 text-right font-medium">{t("ml.f1")}</th>
                <th className="p-3 text-right font-medium">{t("ml.trainSize")}</th>
                <th className="p-3 text-right font-medium">{t("ml.feedback")}</th>
                <th className="p-3 font-medium">{t("ml.trained")}</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {list.map((m) => (
                <tr key={m.id} className="border-t border-border">
                  <td className="p-3 font-semibold">{m.version}</td>
                  <td className="p-3">
                    <Badge className={STATUS_CLS[m.status]}>{t(`ml.st.${m.status}`)}</Badge>
                  </td>
                  <td className="p-3 text-right tabular-nums">{pct(m.accuracy)}</td>
                  <td className="p-3 text-right tabular-nums">{m.macro_f1.toFixed(3)}</td>
                  <td className="p-3 text-right tabular-nums">{m.train_size}</td>
                  <td className="p-3 text-right tabular-nums">{m.feedback_count}</td>
                  <td className="whitespace-nowrap p-3 text-muted">{fmtDate(m.trained_at, lang)}</td>
                  <td className="whitespace-nowrap p-1 text-right">
                    <Button size="sm" variant="ghost" onClick={() => setDetail(m.id)}>
                      {t("common.details")}
                    </Button>
                    {m.status === "candidate" && (
                      <Button size="sm" variant="secondary" onClick={() => setSwitching({ m, action: "activate" })}>
                        {t("ml.activate")}
                      </Button>
                    )}
                    {m.status === "archived" && (
                      <Button size="sm" variant="secondary" onClick={() => setSwitching({ m, action: "rollback" })}>
                        <RotateCcw className="h-4 w-4" aria-hidden /> {t("ml.rollback")}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {history.length > 1 && (
        <Card>
          <h2 className="mb-4 font-semibold">{t("ml.overVersions")}</h2>
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={history} margin={{ left: -8, right: 12, top: 8, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--grid)" />
                <XAxis dataKey="version" {...axis} />
                <YAxis
                  {...axis}
                  domain={[Math.max(0, Math.floor(Math.min(...history.map((h) => h.accuracy)) / 5) * 5 - 5), 100]}
                  width={52}
                  allowDecimals={false}
                  tickFormatter={(v: number) => `${Math.round(v)}%`}
                />
                <Tooltip
                  formatter={(v) => [`${v}%`, t("ml.accuracy")]}
                  contentStyle={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, color: "var(--text)" }}
                  cursor={{ stroke: "var(--muted)", strokeWidth: 1 }}
                />
                <Line type="monotone" dataKey="accuracy" name={t("ml.accuracy")} stroke="var(--series-1)" strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      <Modal open={confirmRetrain} onClose={() => setConfirmRetrain(false)} title={t("ml.retrain")}>
        <p className="text-sm">{t("ml.retrainConfirm")}</p>
        <label className="mt-3 flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" className="h-5 w-5" checked={force} onChange={(e) => setForce(e.target.checked)} /> {t("ml.force")}
        </label>
        <FieldError>{error}</FieldError>
        <div className="mt-4 flex gap-2">
          <Button loading={busy} onClick={retrain}>
            {t("common.confirm")}
          </Button>
          <Button variant="ghost" onClick={() => setConfirmRetrain(false)}>
            {t("common.cancel")}
          </Button>
        </div>
      </Modal>

      <Modal open={!!switching} onClose={() => setSwitching(null)} title={switching ? t(switching.action === "rollback" ? "ml.rollback" : "ml.activate") : ""}>
        {switching && <p className="text-sm">{t("ml.activateConfirm", { v: switching.m.version })}</p>}
        <FieldError>{error}</FieldError>
        <div className="mt-4 flex gap-2">
          <Button loading={busy} onClick={doSwitch}>
            {t("common.confirm")}
          </Button>
          <Button variant="ghost" onClick={() => setSwitching(null)}>
            {t("common.cancel")}
          </Button>
        </div>
      </Modal>

      {detail !== null && <ModelDetail id={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

export default function ModelsPage() {
  return (
    <Guard roles={["admin"]}>
      <ModelsView />
    </Guard>
  );
}
