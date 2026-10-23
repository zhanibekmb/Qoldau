"use client";

import {
  DndContext,
  type DragEndEvent,
  DragOverlay,
  type DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import clsx from "clsx";
import { AlertTriangle, GripVertical, User as UserIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { CategoryChip, PriorityBadge, SlaBadge, StatusBadge } from "@/components/badges";
import { Guard } from "@/components/Guard";
import { Select, Spinner, Toast } from "@/components/ui";
import { api, ApiError, qs } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { timeAgo } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRealtimeEvent } from "@/lib/realtime";
import type { RequestCard, UnitMeta } from "@/lib/types";

type Column = "New" | "In Progress" | "Pending Student" | "Closed";
const COLUMNS: Column[] = ["New", "In Progress", "Pending Student", "Closed"];
// Dropping a card on a column requests this status; the API validates the transition (409 otherwise).
const DROP_STATUS: Record<Column, string | null> = {
  New: null,
  "In Progress": "In Progress",
  "Pending Student": "Waiting for Student",
  Closed: "Resolved",
};
const COLUMN_ACCENT: Record<Column, string> = {
  New: "border-t-primary",
  "In Progress": "border-t-high",
  "Pending Student": "border-t-warn",
  Closed: "border-t-ok",
};

type Board = Record<Column, RequestCard[]>;

function sortColumn(cards: RequestCard[], col: Column): RequestCard[] {
  if (col === "Closed") return cards;
  return [...cards].sort(
    (a, b) => b.priority_score - a.priority_score || Number(!!a.assignee) - Number(!!b.assignee) || a.created_at.localeCompare(b.created_at),
  );
}

function CardBody({ r, dragging }: { r: RequestCard; dragging?: boolean }) {
  const critical = r.priority === "Critical";
  return (
    <div
      className={clsx(
        "rounded-md border bg-surface p-3",
        critical ? "pulse-critical" : r.priority === "High" ? "border-high/60" : "border-border",
        dragging && "shadow-lg",
      )}
    >
      <div className="flex items-start gap-2">
        {critical && <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-critical" aria-label="Critical priority" />}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <PriorityBadge priority={r.priority} score={r.priority_score} />
            <SlaBadge sla={r.sla} />
          </div>
          <Link href={`/requests/${r.id}`} className="mt-1.5 block break-words text-sm font-semibold hover:underline" onPointerDown={(e) => e.stopPropagation()}>
            {r.subject}
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted">
            <span className="tabular-nums">{r.id}</span>
            <CategoryChip name={r.category?.name} />
          </div>
          <div className="mt-1.5 flex items-center justify-between gap-2 text-xs text-muted">
            <span className="flex min-w-0 items-center gap-1 truncate">
              <UserIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
              {r.assignee?.name ?? "Unit queue"}
            </span>
            <span className="shrink-0">{timeAgo(r.created_at)}</span>
          </div>
          {r.status !== "Routed" && r.status !== "In Progress" && (
            <div className="mt-1.5">
              <StatusBadge status={r.status} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DraggableCard({ r }: { r: RequestCard }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: r.id, data: { card: r } });
  return (
    <li ref={setNodeRef} className={clsx("relative touch-manipulation", isDragging && "opacity-30")}>
      <button
        {...listeners}
        {...attributes}
        aria-label={`Move ${r.id}`}
        className="absolute right-1 top-1 z-10 grid h-11 w-11 cursor-grab place-items-center rounded-md text-muted hover:bg-surface-2 active:cursor-grabbing"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div {...listeners} className="cursor-grab pr-8 active:cursor-grabbing">
        <CardBody r={r} />
      </div>
    </li>
  );
}

function DropColumn({ col, cards, label }: { col: Column; cards: RequestCard[]; label: string }) {
  const { setNodeRef, isOver } = useDroppable({ id: col, disabled: !DROP_STATUS[col] });
  return (
    <section
      ref={setNodeRef}
      aria-label={label}
      className={clsx(
        "flex w-[85vw] max-w-sm shrink-0 snap-start flex-col rounded-lg border-t-4 bg-surface-2 md:w-auto md:max-w-none",
        COLUMN_ACCENT[col],
        isOver && "ring-2 ring-primary",
      )}
    >
      <header className="flex items-center justify-between px-3 py-2">
        <h2 className="text-sm font-semibold">{label}</h2>
        <span className="text-sm font-semibold tabular-nums text-muted">{cards.length}</span>
      </header>
      <ul className="flex min-h-24 flex-1 flex-col gap-2 overflow-y-auto px-2 pb-3 md:max-h-[calc(100vh-14rem)]">
        {cards.map((r) => (
          <DraggableCard key={r.id} r={r} />
        ))}
      </ul>
    </section>
  );
}

function BoardView() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [board, setBoard] = useState<Board | null>(null);
  const [mine, setMine] = useState(false);
  const [units, setUnits] = useState<UnitMeta[]>([]);
  const [unitId, setUnitId] = useState<string>("");
  const [active, setActive] = useState<RequestCard | null>(null);
  const [toast, setToast] = useState<{ msg: string; tone: "info" | "error" } | null>(null);
  const reloadTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const isAdmin = user?.role === "admin";

  const load = useCallback(() => {
    api<{ columns: Board }>(`/requests/board${qs({ mine, unit_id: isAdmin ? unitId : undefined })}`)
      .then((d) => setBoard(d.columns))
      .catch(() => {});
  }, [mine, unitId, isAdmin]);

  useEffect(load, [load]);
  useEffect(() => {
    if (isAdmin) api<UnitMeta[]>("/meta/units").then(setUnits).catch(() => {});
  }, [isAdmin]);
  // Live: another agent moved a card, a new request was routed, SLA escalation...
  useRealtimeEvent((e) => {
    if (["request_updated", "request_new", "status_changed"].includes(e.event)) {
      clearTimeout(reloadTimer.current);
      reloadTimer.current = setTimeout(load, 300);
    }
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 180, tolerance: 8 } }),
    useSensor(KeyboardSensor),
  );

  const onStart = (e: DragStartEvent) => setActive((e.active.data.current?.card as RequestCard) ?? null);

  async function onEnd(e: DragEndEvent) {
    setActive(null);
    const card = e.active.data.current?.card as RequestCard | undefined;
    const to = e.over?.id as Column | undefined;
    if (!board || !card || !to) return;
    const from = COLUMNS.find((c) => board[c].some((x) => x.id === card.id));
    if (!from || from === to || !DROP_STATUS[to]) return;

    const snapshot = board;
    // Optimistic: the card locks into the new column immediately.
    setBoard({
      ...board,
      [from]: board[from].filter((x) => x.id !== card.id),
      [to]: sortColumn([{ ...card, status: DROP_STATUS[to]! }, ...board[to]], to),
    });
    try {
      const updated = await api<RequestCard>(`/requests/${card.id}/status`, { method: "PATCH", json: { status: DROP_STATUS[to] } });
      setBoard((b) => b && { ...b, [to]: sortColumn(b[to].map((x) => (x.id === card.id ? { ...x, ...updated } : x)), to) });
      setToast({ msg: t("board.moved", { col: t(`status.${DROP_STATUS[to]}`) }), tone: "info" });
    } catch (err) {
      setBoard(snapshot);
      const detail = err instanceof ApiError && err.status === 409 ? `${t("board.dropError")}: ${card.status} → ${DROP_STATUS[to]}` : t("common.error");
      setToast({ msg: detail, tone: "error" });
    }
  }

  const labels: Record<Column, string> = {
    New: t("board.new"),
    "In Progress": t("status.In Progress"),
    "Pending Student": t("status.Waiting for Student"),
    Closed: t("status.Resolved"),
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="mr-auto text-2xl font-bold">
          {t("board.title")}
          {user?.unit_name && <span className="ml-2 text-base font-normal text-muted">· {user.unit_name}</span>}
        </h1>
        {isAdmin && (
          <Select aria-label="Unit" value={unitId} onChange={(e) => setUnitId(e.target.value)} className="w-auto">
            <option value="">All units</option>
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </Select>
        )}
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" className="h-5 w-5" checked={mine} onChange={(e) => setMine(e.target.checked)} />
          {t("board.mine")}
        </label>
      </div>
      {!board ? (
        <Spinner label={t("common.loading")} />
      ) : (
        <DndContext sensors={sensors} onDragStart={onStart} onDragEnd={onEnd} onDragCancel={() => setActive(null)}>
          <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-2 md:mx-0 md:grid md:grid-cols-4 md:overflow-visible md:px-0">
            {COLUMNS.map((c) => (
              <DropColumn key={c} col={c} cards={board[c]} label={labels[c]} />
            ))}
          </div>
          <DragOverlay>{active ? <CardBody r={active} dragging /> : null}</DragOverlay>
        </DndContext>
      )}
      {toast && <Toast message={toast.msg} tone={toast.tone} onDone={() => setToast(null)} />}
    </div>
  );
}

export default function BoardPage() {
  return (
    <Guard roles={["agent", "unit_head", "admin"]}>
      <BoardView />
    </Guard>
  );
}
