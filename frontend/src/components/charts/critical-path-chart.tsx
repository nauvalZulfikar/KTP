"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { TaskRead } from "@/lib/types";

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const MS_PER_WEEK = 7 * MS_PER_DAY;
const BUSINESS_MIN_PER_DAY = 480;
const BAR_HEIGHT_PX = 28;
const LABEL_HEIGHT_PX = 14;
const SLOT_HEIGHT_PX = BAR_HEIGHT_PX + LABEL_HEIGHT_PX + 2;
const LANE_PAD_PX = 4;
const TOUCH_THRESHOLD_MS = MS_PER_DAY * 0.01;

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

function fmtWeek(ms: number): string {
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

function computeNoSplitBars(tasks: TaskRead[]): Bar[] {
  const sorted = [...tasks].sort((a, b) => {
    const dA = new Date(a.promised_delivery_date).getTime();
    const dB = new Date(b.promised_delivery_date).getTime();
    if (dA !== dB) return dA - dB;
    if (a.product_name !== b.product_name) return a.product_name.localeCompare(b.product_name);
    return a.component.localeCompare(b.component);
  });

  let globalInHouseEnd = 0;
  const productLastEnd = new Map<string, number>();
  const bars: Bar[] = [];

  for (const t of sorted) {
    const orderMs = new Date(t.order_processing_date).getTime();
    const prevComp = productLastEnd.get(t.product_name) ?? 0;
    const isOut = t.machine_number === "OutSrc";
    const startMs = isOut
      ? Math.max(orderMs, prevComp)
      : Math.max(orderMs, prevComp, globalInHouseEnd);
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
    if (!isOut) globalInHouseEnd = endMs;
    productLastEnd.set(t.product_name, endMs);
  }

  return bars;
}

export function CriticalPathChart() {
  const { data: tasks, error, isLoading } = useSWR<TaskRead[]>("/tasks/original", fetcher);

  const { bars, products, minMs, maxMs, weekTicks, lanesPerProduct } = useMemo(() => {
    if (!tasks) {
      return {
        bars: [] as Bar[],
        products: [] as string[],
        minMs: 0,
        maxMs: 0,
        weekTicks: [] as number[],
        lanesPerProduct: new Map<string, number>(),
      };
    }
    const bars = computeNoSplitBars(tasks);
    const products = Array.from(new Set(bars.map((b) => b.product))).sort();
    const minMs = bars.length ? Math.min(...bars.map((b) => b.startMs)) : 0;
    const maxMs = bars.length ? Math.max(...bars.map((b) => b.endMs)) : 0;

    const start = new Date(minMs);
    start.setHours(0, 0, 0, 0);
    const day = start.getDay();
    const mondayOffset = day === 0 ? -6 : 1 - day;
    start.setDate(start.getDate() + mondayOffset);
    const weekTicks: number[] = [];
    for (let t = start.getTime(); t <= maxMs + MS_PER_WEEK; t += MS_PER_WEEK) weekTicks.push(t);

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
        Loading original tasks...
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

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
        <h3 className="text-sm font-medium">
          Original Scheduling
        </h3>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-full">
          {/* product rows */}
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
                className="flex border-b border-zinc-100 dark:border-zinc-800"
              >
                <div className="w-28 shrink-0 px-3 text-sm font-medium border-r border-zinc-200 dark:border-zinc-800 flex items-center">
                  {p}
                </div>
                <div className="relative flex-1" style={{ height: rowHeight }}>
                  {/* weekly grid lines */}
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
                  {/* separator lines between touching bars */}
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
                  {/* bars + machine labels */}
                  {rowBars.map((b) => {
                    const left = pct(b.startMs);
                    const width = Math.max(0.3, pct(b.endMs) - left);
                    const slotTop = LANE_PAD_PX + b.lane * SLOT_HEIGHT_PX;
                    const color = componentColor(b.component);
                    const barStyle: React.CSSProperties = {
                      left: `${left}%`,
                      width: `${width}%`,
                      minWidth: 4,
                      top: slotTop,
                      height: BAR_HEIGHT_PX,
                      backgroundColor: color,
                      border: "1.5px solid rgba(0,0,0,0.2)",
                    };
                    if (b.outsource) {
                      barStyle.backgroundImage =
                        "repeating-linear-gradient(135deg, rgba(255,255,255,0.25) 0 6px, transparent 6px 12px)";
                    }
                    return (
                      <div key={b.id}>
                        <div
                          title={[
                            `${b.product} \u00b7 ${b.component}`,
                            `Machine: ${b.machine}${b.outsource ? " (Outsource)" : ""}`,
                            `Duration: ${b.durationMin.toFixed(0)} min`,
                            `${fmtDateTime(b.startMs)} \u2192 ${fmtDateTime(b.endMs)}`,
                          ].join("\n")}
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
            <div className="w-28 shrink-0 border-r border-zinc-200 dark:border-zinc-800" />
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
