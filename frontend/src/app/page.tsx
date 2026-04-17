"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import GanttView from "@/components/gantt-view";
import { MetricsTiles } from "@/components/metrics-tiles";
import { ComponentStatusChart } from "@/components/charts/component-status-chart";
import { CriticalPathChart } from "@/components/charts/critical-path-chart";
import { LateProductsChart } from "@/components/charts/late-products-chart";
import { MachineUtilChart } from "@/components/charts/machine-util-chart";
import { UnscheduledDurationChart } from "@/components/charts/unscheduled-duration-chart";
import { WaitingTimeChart } from "@/components/charts/waiting-time-chart";
import { ExportButton } from "@/components/export-button";
import { FloatingWindow } from "@/components/floating-window";
import { RandomiseButton } from "@/components/randomise-button";
import { ModifyPanel } from "@/components/panels/modify-panel";
import { ProductsPanel } from "@/components/panels/products-panel";
import { api, fetcher } from "@/lib/api";
import type { MetricsRead, ScheduleRunDetail, ScheduleRunRead, TaskRead } from "@/lib/types";

const TICK_MS = 400;

export default function DashboardPage() {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runs = useSWR<ScheduleRunRead[]>("/runs", fetcher);
  const latestRunId = runs.data?.[0]?.id ?? null;

  const runDetail = useSWR<ScheduleRunDetail>(
    latestRunId !== null ? `/runs/${latestRunId}` : null,
    fetcher
  );
  const metrics = useSWR<MetricsRead>(
    latestRunId !== null ? `/runs/${latestRunId}/metrics` : null,
    fetcher
  );
  const tasks = useSWR<TaskRead[]>("/tasks", fetcher);

  const sortedAssignments = useMemo(
    () =>
      [...(runDetail.data?.assignments ?? [])].sort((a, b) =>
        a.start_time.localeCompare(b.start_time)
      ),
    [runDetail.data]
  );
  const total = sortedAssignments.length;

  const [visibleCount, setVisibleCount] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [animatedRunId, setAnimatedRunId] = useState<number | null>(null);

  const [modifyOpen, setModifyOpen] = useState(false);
  const [productsOpen, setProductsOpen] = useState(false);

  useEffect(() => {
    if (!runDetail.data || total === 0) return;
    if (runDetail.data.id !== animatedRunId) {
      setAnimatedRunId(runDetail.data.id);
      setVisibleCount(0);
      setPlaying(true);
    } else if (visibleCount === 0 && !playing) {
      setVisibleCount(total);
    }
  }, [runDetail.data, animatedRunId, total, visibleCount, playing]);

  useEffect(() => {
    if (!playing) return;
    if (visibleCount >= total) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setVisibleCount((c) => c + 1), TICK_MS);
    return () => clearTimeout(t);
  }, [playing, visibleCount, total]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      await api.runSchedule();
      await runs.mutate();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const visible = sortedAssignments.slice(0, visibleCount);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-zinc-500">
            {latestRunId !== null
              ? `Showing latest run #${latestRunId}`
              : "No runs yet — run the scheduler to get started."}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setModifyOpen(true)}
            className="px-3 py-2 rounded-md text-sm border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            Modify
          </button>
          <button
            type="button"
            onClick={() => setProductsOpen(true)}
            className="px-3 py-2 rounded-md text-sm border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
          >
            Products
          </button>
          <RandomiseButton
            tasks={tasks.data}
            onChanged={async () => {
              await tasks.mutate();
            }}
            runAfter={async () => {
              await api.runSchedule();
              await runs.mutate();
            }}
          />
          <ExportButton />
          <button
            onClick={handleRun}
            disabled={running}
            className="px-4 py-2 rounded-md bg-sky-600 text-white text-sm font-medium disabled:opacity-50 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-400 shadow-sm"
          >
            {running ? "Running…" : "Run scheduler"}
          </button>
        </div>
      </div>

      <FloatingWindow
        title="Modify"
        open={modifyOpen}
        onClose={() => setModifyOpen(false)}
        width={880}
      >
        <ModifyPanel />
      </FloatingWindow>

      <FloatingWindow
        title="Product List Change"
        open={productsOpen}
        onClose={() => setProductsOpen(false)}
        width={920}
      >
        <ProductsPanel />
      </FloatingWindow>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 text-red-800 p-3 text-sm">
          {error}
        </div>
      )}

      {metrics.data && <MetricsTiles metrics={metrics.data} />}

      {runDetail.data && tasks.data && total > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-lg font-medium">Gantt</h2>
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500 tabular-nums mr-2">
                {visibleCount} / {total}
              </span>
              <button
                type="button"
                onClick={() => {
                  if (visibleCount >= total) setVisibleCount(0);
                  setPlaying(true);
                }}
                disabled={playing}
                className="px-3 py-1.5 rounded-md text-xs border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40"
              >
                Play
              </button>
              <button
                type="button"
                onClick={() => setPlaying(false)}
                disabled={!playing}
                className="px-3 py-1.5 rounded-md text-xs border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40"
              >
                Pause
              </button>
              <button
                type="button"
                onClick={() => {
                  setPlaying(false);
                  setVisibleCount(total);
                }}
                className="px-3 py-1.5 rounded-md text-xs border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                Show all
              </button>
              <button
                type="button"
                onClick={() => {
                  setVisibleCount(0);
                  setPlaying(false);
                }}
                className="px-3 py-1.5 rounded-md text-xs border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                Clear
              </button>
            </div>
          </div>
          <GanttView assignments={visible} tasks={tasks.data} />
        </section>
      )}

      {runDetail.data && tasks.data && total > 0 && (
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ComponentStatusChart assignments={runDetail.data.assignments} tasks={tasks.data} />
          {metrics.data && <LateProductsChart data={metrics.data.late_counts} />}
        </section>
      )}

      {metrics.data && (
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <MachineUtilChart data={metrics.data.machine_utilization} />
          <WaitingTimeChart
            title="Product Waiting Time"
            xLabel="Product"
            data={metrics.data.product_waiting_days}
          />
          <WaitingTimeChart
            title="Component Waiting Time"
            xLabel="Component"
            data={metrics.data.component_waiting_days}
            palette={["#8b5cf6", "#06b6d4", "#84cc16", "#ec4899", "#6366f1", "#f97316"]}
          />
        </section>
      )}

      <section>
        <CriticalPathChart />
      </section>

      {tasks.data && tasks.data.length > 0 && (
        <section>
          <UnscheduledDurationChart tasks={tasks.data} />
        </section>
      )}
    </div>
  );
}
