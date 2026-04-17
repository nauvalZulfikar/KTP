"use client";

import { useMemo, useState } from "react";
import type { ScheduledAssignmentRead, TaskRead } from "@/lib/types";

type Props = {
  assignments: ScheduledAssignmentRead[];
  tasks: TaskRead[];
};

type Bar = {
  key: string;
  assignmentId: number;
  product: string;
  label: string;
  tooltip: string;
  machine: string;
  startMs: number;
  endMs: number;
  outsource: boolean;
};

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 8;
const ZOOM_STEP = 1.5;

const PRODUCT_PALETTE = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#84cc16", "#ec4899",
  "#6366f1", "#f97316", "#14b8a6", "#d946ef",
];

function productColor(product: string): string {
  let hash = 0;
  for (let i = 0; i < product.length; i++) hash = (hash * 31 + product.charCodeAt(i)) | 0;
  return PRODUCT_PALETTE[Math.abs(hash) % PRODUCT_PALETTE.length];
}

function startOfDay(ms: number): number {
  const d = new Date(ms);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

function fmtDate(ms: number): string {
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

export default function GanttView({ assignments, tasks }: Props) {
  const [zoom, setZoom] = useState(1);

  const taskById = useMemo(() => {
    const m = new Map<number, TaskRead>();
    for (const t of tasks) m.set(t.id, t);
    return m;
  }, [tasks]);

  const { bars, machines, minMs, maxMs, dayTicks } = useMemo(() => {
    const bars: Bar[] = assignments.map((a) => {
      const t = taskById.get(a.task_id);
      const machine = t?.machine_number ?? "—";
      const product = t?.product_name ?? "—";
      const label = t
        ? `${product} · ${t.component}${a.split_index > 0 ? ` (split ${a.split_index})` : ""}`
        : `#${a.task_id}`;
      const startMs = new Date(a.start_time).getTime();
      const endMs = new Date(a.end_time).getTime();
      return {
        key: `a-${a.id}`,
        assignmentId: a.id,
        product,
        label,
        tooltip: `${label}\nMachine: ${machine}\nQty: ${a.assigned_quantity}\n${fmtDateTime(startMs)} → ${fmtDateTime(endMs)}`,
        machine,
        startMs,
        endMs,
        outsource: machine === "OutSrc",
      };
    });
    const machines = Array.from(new Set(bars.map((b) => b.machine))).sort();
    const minMs = bars.length ? Math.min(...bars.map((b) => b.startMs)) : 0;
    const maxMs = bars.length ? Math.max(...bars.map((b) => b.endMs)) : 0;
    const dayTicks: number[] = [];
    if (bars.length) {
      for (let t = startOfDay(minMs); t <= maxMs; t += MS_PER_DAY) dayTicks.push(t);
    }
    return { bars, machines, minMs, maxMs, dayTicks };
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

      {/* Scrollable timeline */}
      <div className="overflow-x-auto">
        <div style={innerStyle}>
          {/* Header row — date ticks */}
          <div className="flex border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
            <div className="w-24 shrink-0 sticky left-0 z-20 bg-zinc-50 dark:bg-zinc-900 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-500 border-r border-zinc-200 dark:border-zinc-800">
              Machine
            </div>
            <div className="relative flex-1 h-8">
              {dayTicks.map((t) => {
                const left = pct(t);
                if (left < 0 || left > 100) return null;
                return (
                  <div
                    key={t}
                    className="absolute top-0 bottom-0 border-l border-zinc-200 dark:border-zinc-800"
                    style={{ left: `${left}%` }}
                  >
                    <span className="absolute top-1 left-1 text-[10px] text-zinc-500 whitespace-nowrap">
                      {fmtDate(t)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Machine rows */}
          {machines.map((m) => {
            const rowBars = bars.filter((b) => b.machine === m);
            return (
              <div
                key={m}
                className="flex border-b last:border-b-0 border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50/50 dark:hover:bg-zinc-900/50"
              >
                <div className="w-24 shrink-0 sticky left-0 z-10 bg-white dark:bg-zinc-950 px-3 py-3 font-mono text-sm border-r border-zinc-200 dark:border-zinc-800 flex items-center">
                  {m}
                </div>
                <div className="relative flex-1 h-12">
                  {dayTicks.map((t) => {
                    const left = pct(t);
                    if (left < 0 || left > 100) return null;
                    return (
                      <div
                        key={t}
                        className="absolute top-0 bottom-0 border-l border-zinc-100 dark:border-zinc-800 pointer-events-none"
                        style={{ left: `${left}%` }}
                      />
                    );
                  })}
                  {rowBars.map((b) => {
                    const left = pct(b.startMs);
                    const width = Math.max(0.3, pct(b.endMs) - left);
                    const color = productColor(b.product);
                    const style: React.CSSProperties = {
                      left: `${left}%`,
                      width: `${width}%`,
                      minWidth: 4,
                      backgroundColor: color,
                    };
                    if (b.outsource) {
                      style.backgroundImage =
                        "repeating-linear-gradient(135deg, rgba(255,255,255,0.25) 0 6px, transparent 6px 12px)";
                    }
                    return (
                      <div
                        key={b.key}
                        title={b.tooltip}
                        className="absolute top-1.5 h-9 rounded px-2 text-xs font-medium flex items-center overflow-hidden whitespace-nowrap shadow-sm cursor-pointer text-white ring-1 ring-black/10 hover:brightness-110 transition"
                        style={style}
                      >
                        <span className="truncate">{b.label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend — full width, not zoomed */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 px-4 py-2 text-xs text-zinc-600 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
        {Array.from(new Set(bars.map((b) => b.product)))
          .sort()
          .map((p) => (
            <div key={p} className="flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-3 rounded"
                style={{ backgroundColor: productColor(p) }}
              />
              {p}
            </div>
          ))}
        <div className="flex items-center gap-1.5 ml-auto">
          <span
            className="inline-block w-4 h-3 rounded"
            style={{
              backgroundColor: "#71717a",
              backgroundImage:
                "repeating-linear-gradient(135deg, rgba(255,255,255,0.35) 0 4px, transparent 4px 8px)",
            }}
          />
          stripes = OutSrc
        </div>
      </div>
    </div>
  );
}
