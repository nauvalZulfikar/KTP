"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { TaskRead } from "@/lib/types";

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const BUSINESS_MIN_PER_DAY = 480; // 8h / day

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

function fmtDate(ms: number): string {
  return new Date(ms).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function fmtDateTime(ms: number): string {
  return new Date(ms).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

type Bar = {
  id: number;
  product: string;
  component: string;
  machine: string;
  startMs: number;
  endMs: number;
  durationMin: number;
  outsource: boolean;
  lane: number;
};

/**
 * FCFS schedule without job splitting.
 *   - component dependency preserved (C2 waits for C1 in the same product)
 *   - machine sequencing preserved for real machines (one job at a time)
 *   - OutSrc stays parallel (infinite capacity), matching the real scheduler
 *   - no gap-splitting: a job that could theoretically slide into a gap just
 *     waits until the machine is fully free, as one continuous block
 */
function computeNoSplitBars(tasks: TaskRead[]): Bar[] {
  const sorted = [...tasks].sort((a, b) => {
    const dA = new Date(a.promised_delivery_date).getTime();
    const dB = new Date(b.promised_delivery_date).getTime();
    if (dA !== dB) return dA - dB;
    if (a.product_name !== b.product_name) return a.product_name.localeCompare(b.product_name);
    return a.component.localeCompare(b.component);
  });

  const machineLastEnd = new Map<string, number>();
  const productLastEnd = new Map<string, number>();
  const bars: Bar[] = [];

  for (const t of sorted) {
    const orderMs = new Date(t.order_processing_date).getTime();
    const prevComp = productLastEnd.get(t.product_name) ?? 0;
    const isOut = t.machine_number === "OutSrc";
    const mEnd = isOut ? 0 : machineLastEnd.get(t.machine_number) ?? 0;
    const startMs = Math.max(orderMs, prevComp, mEnd);
    const durationMin = (t.quantity_required * t.run_time_per_1000) / 1000;
    const durationMs = (durationMin / BUSINESS_MIN_PER_DAY) * MS_PER_DAY;
    const endMs = startMs + durationMs;
    bars.push({
      id: t.id,
      product: t.product_name,
      component: t.component,
      machine: t.machine_number,
      startMs,
      endMs,
      durationMin,
      outsource: isOut,
      lane: 0,
    });
    if (!isOut) machineLastEnd.set(t.machine_number, endMs);
    productLastEnd.set(t.product_name, endMs);
  }

  // Assign lanes only for OutSrc (real machines are inherently single-lane).
  const outsrcBars = bars.filter((b) => b.outsource);
  outsrcBars.sort((a, b) => a.startMs - b.startMs);
  const laneEnds: number[] = [];
  for (const b of outsrcBars) {
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

  return bars;
}

export function CriticalPathChart() {
  const { data: tasks, error, isLoading } = useSWR<TaskRead[]>("/tasks/original", fetcher);

  const { bars, machines, minMs, maxMs, dayTicks, lanesPerMachine } = useMemo(() => {
    if (!tasks) {
      return {
        bars: [] as Bar[],
        machines: [] as string[],
        minMs: 0,
        maxMs: 0,
        dayTicks: [] as number[],
        lanesPerMachine: new Map<string, number>(),
      };
    }
    const bars = computeNoSplitBars(tasks);
    const machines = Array.from(new Set(bars.map((b) => b.machine))).sort();
    const minMs = bars.length ? Math.min(...bars.map((b) => b.startMs)) : 0;
    const maxMs = bars.length ? Math.max(...bars.map((b) => b.endMs)) : 0;
    const start = new Date(minMs);
    start.setHours(0, 0, 0, 0);
    const dayTicks: number[] = [];
    for (let t = start.getTime(); t <= maxMs; t += MS_PER_DAY) dayTicks.push(t);
    const lanesPerMachine = new Map<string, number>();
    for (const b of bars) {
      lanesPerMachine.set(b.machine, Math.max(lanesPerMachine.get(b.machine) ?? 1, b.lane + 1));
    }
    return { bars, machines, minMs, maxMs, dayTicks, lanesPerMachine };
  }, [tasks]);

  if (error) {
    return (
      <div className="rounded-lg border border-red-300 bg-red-50 text-red-800 p-4 text-sm">
        Failed to load original tasks: {String(error)}
      </div>
    );
  }
  if (isLoading || !tasks) {
    return (
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 text-center text-sm text-zinc-500">
        Loading original tasks…
      </div>
    );
  }
  if (bars.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-10 text-center text-sm text-zinc-500">
        No original tasks in the Excel source.
      </div>
    );
  }

  const range = Math.max(1, maxMs - minMs);
  const pct = (ms: number) => ((ms - minMs) / range) * 100;
  const BAR_HEIGHT_PX = 36;
  const LANE_PAD_PX = 6;

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <h3 className="text-sm font-medium">
          No Machine Sequencing and Job Splitting (MSJS){" "}
          <span className="text-xs text-zinc-500">
            (original Excel — component order preserved, one job at a time per machine, each
            component is a single continuous bar with no gap-filling splits)
          </span>
        </h3>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-full">
          {/* header */}
          <div className="flex border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
            <div className="w-24 shrink-0 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-zinc-500 border-r border-zinc-200 dark:border-zinc-800">
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

          {machines.map((m) => {
            const rowBars = bars.filter((b) => b.machine === m);
            const lanes = lanesPerMachine.get(m) ?? 1;
            const rowHeight = lanes * BAR_HEIGHT_PX + LANE_PAD_PX * 2;
            return (
              <div
                key={m}
                className="flex border-b last:border-b-0 border-zinc-100 dark:border-zinc-800"
              >
                <div className="w-24 shrink-0 px-3 font-mono text-sm border-r border-zinc-200 dark:border-zinc-800 flex items-center">
                  {m}
                </div>
                <div className="relative flex-1" style={{ height: rowHeight }}>
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
                    const top = LANE_PAD_PX + b.lane * BAR_HEIGHT_PX;
                    const color = productColor(b.product);
                    const style: React.CSSProperties = {
                      left: `${left}%`,
                      width: `${width}%`,
                      minWidth: 4,
                      top,
                      height: BAR_HEIGHT_PX - 4,
                      backgroundColor: color,
                    };
                    if (b.outsource) {
                      style.backgroundImage =
                        "repeating-linear-gradient(135deg, rgba(255,255,255,0.25) 0 6px, transparent 6px 12px)";
                    }
                    return (
                      <div
                        key={b.id}
                        title={`${b.product} · ${b.component}\n${b.durationMin.toFixed(0)} min\n${fmtDateTime(b.startMs)} → ${fmtDateTime(b.endMs)}`}
                        className="absolute rounded px-2 text-xs font-medium flex items-center overflow-hidden whitespace-nowrap shadow-sm cursor-pointer text-white ring-1 ring-black/10 hover:brightness-110 transition"
                        style={style}
                      >
                        <span className="truncate">{b.product} · {b.component}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

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
