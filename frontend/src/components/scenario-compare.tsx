"use client";

import { useMemo } from "react";
import GanttView from "./gantt-view";
import {
  computeScenarioDiff,
  formatDurationDelta,
  type DiffStatus,
  type ScenarioSnapshot,
} from "@/lib/scenario-diff";

type Props = {
  baseline: ScenarioSnapshot;
  candidate: ScenarioSnapshot;
};

const STATUS_LABEL: Record<DiffStatus, string> = {
  same: "Same",
  moved: "Moved",
  "machine-changed": "Machine changed",
  added: "Added",
  removed: "Removed",
};

const STATUS_STYLE: Record<DiffStatus, string> = {
  same: "text-zinc-500 border-zinc-300 dark:border-zinc-700",
  moved: "text-amber-700 dark:text-amber-400 border-amber-500",
  "machine-changed": "text-red-700 dark:text-red-400 border-red-500",
  added: "text-emerald-700 dark:text-emerald-400 border-emerald-500",
  removed: "text-rose-700 dark:text-rose-400 border-rose-500",
};

export function ScenarioCompare({ baseline, candidate }: Props) {
  const diff = useMemo(() => computeScenarioDiff(baseline, candidate), [baseline, candidate]);

  const changedDiffs = diff.diffs.filter((d) => d.status !== "same");

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
        <div className="flex flex-wrap items-baseline gap-3 mb-3">
          <h3 className="text-sm font-semibold">
            Diff: <span className="text-sky-600 dark:text-sky-400">{baseline.name}</span>
            <span className="mx-2 text-zinc-400">vs</span>
            <span className="text-violet-600 dark:text-violet-400">{candidate.name}</span>
          </h3>
          <span className="text-xs text-zinc-500">
            {changedDiffs.length} change{changedDiffs.length === 1 ? "" : "s"} out of {diff.summary.total} tasks
          </span>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge status="same" count={diff.summary.same} />
          <Badge status="moved" count={diff.summary.moved} />
          <Badge status="machine-changed" count={diff.summary.machineChanged} />
          <Badge status="added" count={diff.summary.added} />
          <Badge status="removed" count={diff.summary.removed} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-2">
          <div className="text-sm font-medium text-sky-600 dark:text-sky-400">
            A · {baseline.name}
          </div>
          <GanttView
            assignments={baseline.assignments}
            tasks={baseline.tasks}
            diffStatusMap={diff.statusByTaskIdA}
          />
        </div>
        <div className="space-y-2">
          <div className="text-sm font-medium text-violet-600 dark:text-violet-400">
            B · {candidate.name}
          </div>
          <GanttView
            assignments={candidate.assignments}
            tasks={candidate.tasks}
            diffStatusMap={diff.statusByTaskIdB}
          />
        </div>
      </div>

      {changedDiffs.length > 0 && (
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden">
          <div className="px-4 py-2 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Changes ({changedDiffs.length})
          </div>
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-zinc-50 dark:bg-zinc-900 text-zinc-500">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Status</th>
                  <th className="text-left px-3 py-2 font-medium">Task</th>
                  <th className="text-left px-3 py-2 font-medium">Product</th>
                  <th className="text-left px-3 py-2 font-medium">Component</th>
                  <th className="text-left px-3 py-2 font-medium">Machine A → B</th>
                  <th className="text-left px-3 py-2 font-medium">Start Δ</th>
                  <th className="text-left px-3 py-2 font-medium">End Δ</th>
                </tr>
              </thead>
              <tbody>
                {changedDiffs.map((d) => (
                  <tr
                    key={d.taskId}
                    className="border-t border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50/70 dark:hover:bg-zinc-900/70"
                  >
                    <td className="px-3 py-1.5">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded border text-[10px] font-medium ${STATUS_STYLE[d.status]}`}
                      >
                        {STATUS_LABEL[d.status]}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 tabular-nums">#{d.taskId}</td>
                    <td className="px-3 py-1.5">{d.product}</td>
                    <td className="px-3 py-1.5">{d.component}</td>
                    <td className="px-3 py-1.5">
                      {d.aMachine ?? "—"}
                      {d.aMachine !== d.bMachine && (
                        <span className="mx-1 text-zinc-400">→</span>
                      )}
                      {d.aMachine !== d.bMachine && (d.bMachine ?? "—")}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums">
                      {d.startDeltaMs !== undefined ? formatDurationDelta(d.startDeltaMs) : "—"}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums">
                      {d.endDeltaMs !== undefined ? formatDurationDelta(d.endDeltaMs) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Badge({ status, count }: { status: DiffStatus; count: number }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded border ${STATUS_STYLE[status]} bg-white dark:bg-zinc-950`}
    >
      <span className="font-medium">{STATUS_LABEL[status]}</span>
      <span className="tabular-nums">{count}</span>
    </span>
  );
}
