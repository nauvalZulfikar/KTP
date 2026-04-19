"use client";

import { useMemo, useState } from "react";
import type { DiffStatus } from "@/lib/scenario-diff";
import type { ScheduledAssignmentRead, TaskRead } from "@/lib/types";

type Props = {
  assignments: ScheduledAssignmentRead[];
  tasks: TaskRead[];
  diffStatusMap?: Map<number, DiffStatus>;
};

type Bar = {
  key: string;
  assignmentId: number;
  taskId: number;
  product: string;
  component: string;
  machine: string;
  tooltip: string;
  startMs: number;
  endMs: number;
  outsource: boolean;
  lane: number;
};

const DIFF_OUTLINE: Record<DiffStatus, string | null> = {
  same: null,
  moved: "3px solid #f59e0b",
  "machine-changed": "3px solid #ef4444",
  added: "3px solid #10b981",
  removed: "3px dashed #f43f5e",
};

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const MS_PER_WEEK = 7 * MS_PER_DAY;
const BAR_HEIGHT_PX = 28;
const LABEL_HEIGHT_PX = 14;
const SLOT_HEIGHT_PX = BAR_HEIGHT_PX + LABEL_HEIGHT_PX + 2;
const LANE_PAD_PX = 4;
const TOUCH_THRESHOLD_MS = MS_PER_DAY * 0.01;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 8;
const ZOOM_STEP = 1.5;

const COMPONENT_COLORS: Record<string, string> = {
  C1: "#3b82f6",
  C2: "#10b981",
  C3: "#f59e0b",
  C4: "#ef4444",
  C5: "#8b5cf6",
  C6: "#06b6d4",
};

const FALLBACK_PALETTE = [
  "#84cc16", "#ec4899", "#6366f1", "#f97316",
  "#14b8a6", "#d946ef",
];

function componentColor(component: string): string {
  if (COMPONENT_COLORS[component]) return COMPONENT_COLORS[component];
  let hash = 0;
  for (let i = 0; i < component.length; i++) hash = (hash * 31 + component.charCodeAt(i)) | 0;
  return FALLBACK_PALETTE[Math.abs(hash) % FALLBACK_PALETTE.length];
}

function startOfWeek(ms: number): number {
  const d = new Date(ms);
  d.setHours(0, 0, 0, 0);
  const day = d.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + mondayOffset);
  return d.getTime();
}

function fmtWeek(ms: number): string {
  return new Date(ms).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function fmtDateTime(ms: number): string {
  return new Date(ms).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

export default function GanttView({ assignments, tasks, diffStatusMap }: Props) {
  const [zoom, setZoom] = useState(1);

  const taskById = useMemo(() => {
    const m = new Map<number, TaskRead>();
    for (const t of tasks) m.set(t.id, t);
    return m;
  }, [tasks]);

  const { bars, products, minMs, maxMs, weekTicks, lanesPerProduct } = useMemo(() => {
    const bars: Bar[] = assignments.map((a) => {
      const t = taskById.get(a.task_id);
      const machine = t?.machine_number ?? "\u2014";
      const product = t?.product_name ?? "\u2014";
      const component = t?.component ?? "\u2014";
      const splitSuffix = a.split_index > 0 ? ` (split ${a.split_index})` : "";
      const startMs = new Date(a.start_time).getTime();
      const endMs = new Date(a.end_time).getTime();
      return {
        key: `a-${a.id}`,
        assignmentId: a.id,
        taskId: a.task_id,
        product,
        component,
        machine,
        tooltip: [
          `${product} \u00b7 ${component}${splitSuffix}`,
          `Machine: ${machine}${machine === "OutSrc" ? " (Outsource)" : ""}`,
          `Qty: ${a.assigned_quantity}`,
          `${fmtDateTime(startMs)} \u2192 ${fmtDateTime(endMs)}`,
        ].join("\n"),
        startMs,
        endMs,
        outsource: machine === "OutSrc",
        lane: 0,
      };
    });

    const products = Array.from(new Set(bars.map((b) => b.product))).sort();
    const minMs = bars.length ? Math.min(...bars.map((b) => b.startMs)) : 0;
    const maxMs = bars.length ? Math.max(...bars.map((b) => b.endMs)) : 0;

    const weekTicks: number[] = [];
    if (bars.length) {
      for (let t = startOfWeek(minMs); t <= maxMs + MS_PER_WEEK; t += MS_PER_WEEK) weekTicks.push(t);
    }

    const lanesPerProduct = new Map<string, number>();
    for (const p of products) {
      const productBars = bars.filter((b) => b.product === p);
      productBars.sort((a, b) => a.startMs - b.startMs);
      const laneEnds: number[] = [];
      for (const b of productBars) {
        let lane = -1;
        for (let i = 0; i < laneEnds.length; i++) {
          if (laneEnds[i] <= b.startMs) {
            lane = i;
            laneEnds[i] = b.endMs;
            break;
          }
        }
        if (lane === -1) {
          lane = laneEnds.length;
          laneEnds.push(b.endMs);
        }
        b.lane = lane;
      }
      lanesPerProduct.set(p, Math.max(1, laneEnds.length));
    }

    return { bars, products, minMs, maxMs, weekTicks, lanesPerProduct };
  }, [assignments, taskById]);

  if (bars.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-10 text-center text-sm text-zinc-500">
        Press Play to animate, or Show all to render the whole schedule.
      </div>
    );
  }

  const range = Math.max(1, maxMs - minMs);
  const pct = (ms: number) => ((ms - minMs) / range) * 100;

  const innerStyle: React.CSSProperties = {
    minWidth: "100%",
    width: `${zoom * 100}%`,
  };

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden">
      {/* Zoom toolbar */}
      <div className="flex items-center justify-end gap-1 px-3 py-2 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs">
        <span className="text-zinc-500 mr-2 tabular-nums">{Math.round(zoom * 100)}%</span>
        <button
          type="button"
          onClick={() => setZoom((z) => clamp(z / ZOOM_STEP, MIN_ZOOM, MAX_ZOOM))}
          disabled={zoom <= MIN_ZOOM + 1e-6}
          className="w-7 h-7 rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40"
          aria-label="Zoom out"
          title="Zoom out"
        >
          −
        </button>
        <button
          type="button"
          onClick={() => setZoom(1)}
          className="h-7 px-2 rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          title="Reset zoom"
        >
          1:1
        </button>
        <button
          type="button"
          onClick={() => setZoom((z) => clamp(z * ZOOM_STEP, MIN_ZOOM, MAX_ZOOM))}
          disabled={zoom >= MAX_ZOOM - 1e-6}
          className="w-7 h-7 rounded border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40"
          aria-label="Zoom in"
          title="Zoom in"
        >
          +
        </button>
      </div>

      <div className="overflow-x-auto">
        <div style={innerStyle}>
          {/* Product rows */}
          {products.map((p) => {
            const rowBars = bars.filter((b) => b.product === p);
            const lanes = lanesPerProduct.get(p) ?? 1;
            const rowHeight = lanes * SLOT_HEIGHT_PX + LANE_PAD_PX * 2;

            const touchLines: { leftPct: number; top: number }[] = [];
            for (let lane = 0; lane < lanes; lane++) {
              const laneBars = rowBars.filter((b) => b.lane === lane).sort((a, b) => a.startMs - b.startMs);
              for (let i = 0; i < laneBars.length - 1; i++) {
                const gap = laneBars[i + 1].startMs - laneBars[i].endMs;
                if (Math.abs(gap) <= TOUCH_THRESHOLD_MS) {
                  touchLines.push({
                    leftPct: pct(laneBars[i].endMs),
                    top: LANE_PAD_PX + lane * SLOT_HEIGHT_PX,
                  });
                }
              }
            }

            return (
              <div
                key={p}
                className="flex border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50/50 dark:hover:bg-zinc-900/50"
              >
                <div className="w-28 shrink-0 sticky left-0 z-10 bg-white dark:bg-zinc-950 px-3 text-sm font-medium border-r border-zinc-200 dark:border-zinc-800 flex items-center">
                  {p}
                </div>
                <div className="relative flex-1" style={{ height: rowHeight }}>
                  {weekTicks.map((t) => {
                    const left = pct(t);
                    if (left < -5 || left > 105) return null;
                    return (
                      <div
                        key={t}
                        className="absolute top-0 bottom-0 border-l border-zinc-100 dark:border-zinc-800 pointer-events-none"
                        style={{ left: `${left}%` }}
                      />
                    );
                  })}
                  {touchLines.map((tl, i) => (
                    <div
                      key={`sep-${i}`}
                      className="absolute pointer-events-none"
                      style={{
                        left: `${tl.leftPct}%`,
                        top: tl.top,
                        height: BAR_HEIGHT_PX,
                        width: 2,
                        backgroundColor: "rgba(0,0,0,0.3)",
                        zIndex: 5,
                      }}
                    />
                  ))}
                  {rowBars.map((b) => {
                    const left = pct(b.startMs);
                    const width = Math.max(0.3, pct(b.endMs) - left);
                    const slotTop = LANE_PAD_PX + b.lane * SLOT_HEIGHT_PX;
                    const color = componentColor(b.component);
                    const diffStatus = diffStatusMap?.get(b.taskId);
                    const diffBorder = diffStatus ? DIFF_OUTLINE[diffStatus] : null;
                    const barStyle: React.CSSProperties = {
                      left: `${left}%`,
                      width: `${width}%`,
                      minWidth: 4,
                      top: slotTop,
                      height: BAR_HEIGHT_PX,
                      backgroundColor: color,
                      border: diffBorder ?? "1.5px solid rgba(0,0,0,0.2)",
                      boxShadow: diffBorder ? "0 0 0 1px rgba(0,0,0,0.15)" : undefined,
                    };
                    if (b.outsource) {
                      barStyle.backgroundImage =
                        "repeating-linear-gradient(135deg, rgba(255,255,255,0.25) 0 6px, transparent 6px 12px)";
                    }
                    return (
                      <div key={b.key}>
                        <div
                          title={b.tooltip}
                          className="absolute rounded-sm cursor-pointer hover:brightness-110 transition"
                          style={barStyle}
                        />
                        {!b.outsource && (
                          <div
                            className="absolute text-[9px] text-zinc-500 dark:text-zinc-400 text-center whitespace-nowrap overflow-visible pointer-events-none"
                            style={{
                              left: `${left}%`,
                              width: `${width}%`,
                              top: slotTop + BAR_HEIGHT_PX + 1,
                              height: LABEL_HEIGHT_PX,
                              lineHeight: `${LABEL_HEIGHT_PX}px`,
                            }}
                          >
                            {b.machine}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          {/* bottom timeline */}
          <div className="flex bg-zinc-50 dark:bg-zinc-900">
            <div className="w-28 shrink-0 sticky left-0 z-20 bg-zinc-50 dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800" />
            <div className="relative flex-1 h-8">
              {weekTicks.map((t) => {
                const left = pct(t);
                if (left < -5 || left > 105) return null;
                return (
                  <div
                    key={t}
                    className="absolute top-0 bottom-0 border-l border-zinc-300 dark:border-zinc-700"
                    style={{ left: `${left}%` }}
                  >
                    <span className="absolute top-1.5 left-1 text-[10px] text-zinc-500 whitespace-nowrap">
                      {fmtWeek(t)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* legend — components + outsrc inline */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 px-4 py-2 text-xs text-zinc-600 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
        {Array.from(new Set(bars.map((b) => b.component)))
          .sort()
          .map((c) => (
            <div key={c} className="flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-3 rounded"
                style={{ backgroundColor: componentColor(c) }}
              />
              {c}
            </div>
          ))}
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block w-4 h-3 rounded"
            style={{
              backgroundColor: "#71717a",
              backgroundImage:
                "repeating-linear-gradient(135deg, rgba(255,255,255,0.35) 0 4px, transparent 4px 8px)",
            }}
          />
          OutSrc
        </div>
      </div>
    </div>
  );
}
