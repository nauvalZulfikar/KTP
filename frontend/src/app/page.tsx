"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import GanttView from "@/components/gantt-view";
import { ScenarioCompare } from "@/components/scenario-compare";
import { MetricsTiles } from "@/components/metrics-tiles";
import { ComponentStatusChart } from "@/components/charts/component-status-chart";
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
import { computeNonPreemptiveMetrics, computeNonPreemptiveAssignments } from "@/lib/non-preemptive";
import type { ScheduledAssignmentRead, ScheduleRunRead, TaskRead } from "@/lib/types";

const TICK_MS = 400;

type ScenarioTask = TaskRead & {
  start_time?: string | null;
  end_time?: string | null;
};

type ScenarioData = {
  name: string;
  tasks: ScenarioTask[];
};

export default function DashboardPage() {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch scenario list from Excel sheets
  const scenarioList = useSWR<string[]>("/scenarios", fetcher);
  const scenarios = scenarioList.data ?? [];

  // Selected scenario (default to first one, typically "Non-Preempitive")
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const activeScenario = selectedScenario ?? scenarios[0] ?? null;

  // Compare mode state
  const [compareMode, setCompareMode] = useState(false);
  const [compareScenario, setCompareScenario] = useState<string | null>(null);

  // Fetch the selected scenario data
  const scenarioData = useSWR<ScenarioData>(
    activeScenario ? `/scenarios/${encodeURIComponent(activeScenario)}` : null,
    fetcher
  );

  const compareData = useSWR<ScenarioData>(
    compareMode && compareScenario
      ? `/scenarios/${encodeURIComponent(compareScenario)}`
      : null,
    fetcher
  );

  const tasks = useSWR<TaskRead[]>("/tasks", fetcher);
  const runs = useSWR<ScheduleRunRead[]>("/runs", fetcher);

  // Convert scenario tasks to TaskRead[] and ScheduledAssignmentRead[]
  const scenarioTasks: TaskRead[] = useMemo(() => {
    if (!scenarioData.data) return [];
    return scenarioData.data.tasks.map((t) => ({
      id: t.unique_id,
      unique_id: t.unique_id,
      sr_no: t.sr_no,
      product_name: t.product_name,
      order_processing_date: t.order_processing_date,
      promised_delivery_date: t.promised_delivery_date,
      quantity_required: t.quantity_required,
      component: t.component,
      operation: t.operation,
      process_type: t.process_type,
      machine_number: t.machine_number,
      run_time_per_1000: t.run_time_per_1000,
      cycle_time_seconds: t.cycle_time_seconds,
      setup_time_seconds: t.setup_time_seconds,
      status: t.status ?? "InProgress",
    }));
  }, [scenarioData.data]);

  const scenarioAssignments: ScheduledAssignmentRead[] = useMemo(() => {
    if (!scenarioData.data) return [];
    const st = scenarioData.data.tasks;
    // If tasks have start_time/end_time from Excel, use those directly
    const hasSchedule = st.some((t) => t.start_time);
    if (hasSchedule) {
      return st
        .filter((t) => t.start_time && t.end_time)
        .map((t, i) => ({
          id: i + 1,
          run_id: 0,
          task_id: t.unique_id,
          split_index: 0,
          assigned_quantity: t.quantity_required,
          start_time: typeof t.start_time === "string" ? t.start_time : new Date(t.start_time!).toISOString(),
          end_time: typeof t.end_time === "string" ? t.end_time : new Date(t.end_time!).toISOString(),
        }));
    }
    // Otherwise compute non-preemptive schedule
    return computeNonPreemptiveAssignments(scenarioTasks);
  }, [scenarioData.data, scenarioTasks]);

  const scenarioMetrics = useMemo(() => {
    if (scenarioTasks.length === 0 || scenarioAssignments.length === 0) return null;
    return computeNonPreemptiveMetrics(scenarioTasks);
  }, [scenarioTasks, scenarioAssignments]);

  const compareTasks: TaskRead[] = useMemo(() => {
    if (!compareData.data) return [];
    return compareData.data.tasks.map((t) => ({
      id: t.unique_id,
      unique_id: t.unique_id,
      sr_no: t.sr_no,
      product_name: t.product_name,
      order_processing_date: t.order_processing_date,
      promised_delivery_date: t.promised_delivery_date,
      quantity_required: t.quantity_required,
      component: t.component,
      operation: t.operation,
      process_type: t.process_type,
      machine_number: t.machine_number,
      run_time_per_1000: t.run_time_per_1000,
      cycle_time_seconds: t.cycle_time_seconds,
      setup_time_seconds: t.setup_time_seconds,
      status: t.status ?? "InProgress",
    }));
  }, [compareData.data]);

  const compareAssignments: ScheduledAssignmentRead[] = useMemo(() => {
    if (!compareData.data) return [];
    const st = compareData.data.tasks;
    const hasSchedule = st.some((t) => t.start_time);
    if (hasSchedule) {
      return st
        .filter((t) => t.start_time && t.end_time)
        .map((t, i) => ({
          id: i + 1,
          run_id: 0,
          task_id: t.unique_id,
          split_index: 0,
          assigned_quantity: t.quantity_required,
          start_time: typeof t.start_time === "string" ? t.start_time : new Date(t.start_time!).toISOString(),
          end_time: typeof t.end_time === "string" ? t.end_time : new Date(t.end_time!).toISOString(),
        }));
    }
    return computeNonPreemptiveAssignments(compareTasks);
  }, [compareData.data, compareTasks]);

  // Animation
  const total = scenarioAssignments.length;
  const [visibleCount, setVisibleCount] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [animatedScenario, setAnimatedScenario] = useState<string | null>(null);

  const [modifyOpen, setModifyOpen] = useState(false);
  const [productsOpen, setProductsOpen] = useState(false);

  useEffect(() => {
    if (total === 0) return;
    if (activeScenario !== animatedScenario) {
      setAnimatedScenario(activeScenario);
      setVisibleCount(0);
      setPlaying(true);
    } else if (visibleCount === 0 && !playing) {
      setVisibleCount(total);
    }
  }, [activeScenario, animatedScenario, total, visibleCount, playing]);

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

  const visible = scenarioAssignments.slice(0, visibleCount);
  const showGantt = scenarios.length > 0;
  const compareReady =
    compareMode &&
    compareScenario !== null &&
    compareScenario !== activeScenario &&
    compareTasks.length > 0 &&
    scenarioTasks.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-zinc-500">
            {activeScenario
              ? `Showing: ${activeScenario}`
              : "Loading scenarios\u2026"}
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
            {running ? "Running\u2026" : "Run scheduler"}
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

      {scenarioMetrics && <MetricsTiles metrics={scenarioMetrics} />}

      {showGantt && (
        <section className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-lg font-medium">Gantt</h2>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setCompareMode((v) => {
                    const next = !v;
                    if (next && !compareScenario) {
                      const firstOther = scenarios.find((s) => s !== activeScenario) ?? null;
                      setCompareScenario(firstOther);
                    }
                    return next;
                  });
                }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition ${
                  compareMode
                    ? "bg-violet-600 text-white border-violet-600 dark:bg-violet-500 dark:border-violet-500"
                    : "border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                {compareMode ? "Exit compare" : "Compare"}
              </button>
              {!compareMode && (
                <>
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
                </>
              )}
            </div>
          </div>

          {compareMode ? (
            <>
              {compareReady && activeScenario && compareScenario ? (
                <ScenarioCompare
                  baseline={{
                    name: activeScenario,
                    tasks: scenarioTasks,
                    assignments: scenarioAssignments,
                  }}
                  candidate={{
                    name: compareScenario,
                    tasks: compareTasks,
                    assignments: compareAssignments,
                  }}
                />
              ) : (
                <div className="rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 p-6 text-center text-sm text-zinc-500">
                  {compareData.isLoading
                    ? "Loading comparison scenario…"
                    : "Pick a second scenario below to compare."}
                </div>
              )}
              <div className="space-y-2 pt-2">
                <div className="text-xs font-medium text-sky-600 dark:text-sky-400">
                  A · Baseline
                </div>
                <ScenarioButtons
                  scenarios={scenarios}
                  active={activeScenario}
                  disabled={compareScenario}
                  activeClass="bg-sky-600 text-white border-sky-600 dark:bg-sky-500 dark:border-sky-500"
                  onSelect={(name) => {
                    setSelectedScenario(name);
                    setPlaying(false);
                    setVisibleCount(0);
                    setAnimatedScenario(null);
                  }}
                />
                <div className="text-xs font-medium text-violet-600 dark:text-violet-400 pt-2">
                  B · Compare against
                </div>
                <ScenarioButtons
                  scenarios={scenarios}
                  active={compareScenario}
                  disabled={activeScenario}
                  activeClass="bg-violet-600 text-white border-violet-600 dark:bg-violet-500 dark:border-violet-500"
                  onSelect={(name) => setCompareScenario(name)}
                />
              </div>
            </>
          ) : (
            <>
              {scenarioTasks.length > 0 && (
                <GanttView assignments={visible} tasks={scenarioTasks} />
              )}

              {/* Scenario selector buttons */}
              <div className="flex flex-wrap gap-2 pt-2">
                {scenarios.map((name) => {
                  const isActive = activeScenario === name;
                  return (
                    <button
                      key={name}
                      type="button"
                      onClick={() => {
                        setSelectedScenario(name);
                        setPlaying(false);
                        setVisibleCount(0);
                        setAnimatedScenario(null);
                      }}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium border transition ${
                        isActive
                          ? "bg-sky-600 text-white border-sky-600 dark:bg-sky-500 dark:border-sky-500"
                          : "border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                      }`}
                    >
                      {name}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </section>
      )}

      {scenarioAssignments.length > 0 && scenarioTasks.length > 0 && (
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ComponentStatusChart assignments={scenarioAssignments} tasks={scenarioTasks} />
          {scenarioMetrics && <LateProductsChart data={scenarioMetrics.late_counts} />}
        </section>
      )}

      {scenarioMetrics && (
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <MachineUtilChart data={scenarioMetrics.machine_utilization} />
          <WaitingTimeChart
            title="Product Waiting Time"
            xLabel="Product"
            data={scenarioMetrics.product_waiting_days}
          />
          <WaitingTimeChart
            title="Component Waiting Time"
            xLabel="Component"
            data={scenarioMetrics.component_waiting_days}
            palette={["#8b5cf6", "#06b6d4", "#84cc16", "#ec4899", "#6366f1", "#f97316"]}
          />
        </section>
      )}

      {tasks.data && tasks.data.length > 0 && (
        <section>
          <UnscheduledDurationChart tasks={tasks.data} />
        </section>
      )}
    </div>
  );
}

function ScenarioButtons({
  scenarios,
  active,
  disabled,
  activeClass,
  onSelect,
}: {
  scenarios: string[];
  active: string | null;
  disabled: string | null;
  activeClass: string;
  onSelect: (name: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {scenarios.map((name) => {
        const isActive = active === name;
        const isDisabled = disabled === name;
        return (
          <button
            key={name}
            type="button"
            disabled={isDisabled}
            onClick={() => onSelect(name)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium border transition ${
              isActive
                ? activeClass
                : "border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            } ${isDisabled ? "opacity-30 cursor-not-allowed" : ""}`}
          >
            {name}
          </button>
        );
      })}
    </div>
  );
}
