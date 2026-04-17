"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { FloatingWindow } from "./floating-window";
import type { TaskRead } from "@/lib/types";

type Entry = {
  unique_id: number;
  product_name: string;
  component: string;
  machine_number: string;
  before: number;
  after: number;
};

type Props = {
  tasks: TaskRead[] | undefined;
  onChanged: () => Promise<void>;
  runAfter?: () => Promise<void>;
};

const FACTOR_MIN = 0.75;
const FACTOR_MAX = 1.25;
const PICK_MIN_PCT = 0.3;
const PICK_MAX_PCT = 0.6;
const ABSOLUTE_MIN_PICKED = 3;

function shuffled<T>(arr: readonly T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export function RandomiseButton({ tasks, onChanged, runAfter }: Props) {
  const [open, setOpen] = useState(false);
  const [report, setReport] = useState<Entry[] | null>(null);
  const [randomising, setRandomising] = useState(false);
  const [runningScheduler, setRunningScheduler] = useState(false);
  const [ran, setRan] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRandomise() {
    if (!tasks || tasks.length === 0) return;
    setError(null);
    setRandomising(true);
    setRan(false);
    setReport(null);
    try {
      const pool = shuffled(tasks);
      const pickPct = PICK_MIN_PCT + Math.random() * (PICK_MAX_PCT - PICK_MIN_PCT);
      const n = Math.max(
        ABSOLUTE_MIN_PICKED,
        Math.min(pool.length, Math.floor(pool.length * pickPct))
      );
      const picked = pool.slice(0, n);
      const entries: Entry[] = [];
      for (const t of picked) {
        const factor = FACTOR_MIN + Math.random() * (FACTOR_MAX - FACTOR_MIN);
        const nextVal = Math.max(1, Math.round(t.run_time_per_1000 * factor * 10) / 10);
        if (nextVal === t.run_time_per_1000) continue;
        await api.updateTask(t.id, { run_time_per_1000: nextVal });
        entries.push({
          unique_id: t.unique_id,
          product_name: t.product_name,
          component: t.component,
          machine_number: t.machine_number,
          before: t.run_time_per_1000,
          after: nextVal,
        });
      }
      await onChanged();
      setReport(entries);
      setOpen(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRandomising(false);
    }
  }

  async function handleRunFromReport() {
    if (!runAfter) return;
    setError(null);
    setRunningScheduler(true);
    try {
      await runAfter();
      setRan(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunningScheduler(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={handleRandomise}
        disabled={randomising || !tasks}
        className="px-3 py-2 rounded-md text-sm border border-amber-300 text-amber-800 bg-amber-50 hover:bg-amber-100 disabled:opacity-50 shadow-sm"
        title="Randomly vary run_time_per_1000 on 30–60% of components by ±25%"
      >
        {randomising ? "Randomising…" : "Randomise"}
      </button>

      <FloatingWindow
        title="Randomise report"
        open={open}
        onClose={() => setOpen(false)}
        width={760}
      >
        {error && (
          <div className="rounded border border-red-300 bg-red-50 text-red-800 px-3 py-2 text-xs mb-3">
            {error}
          </div>
        )}
        {report && (
          <div className="space-y-4">
            <div className="text-sm text-zinc-700 dark:text-zinc-300">
              Updated <strong>{report.length}</strong> component(s). Run time varied by factor
              <span className="font-mono"> {FACTOR_MIN}x – {FACTOR_MAX}x</span>. Review the changes
              below, then run the scheduler to produce a new run entry.
            </div>
            <div className="overflow-x-auto rounded border border-zinc-200 dark:border-zinc-800">
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-wide text-zinc-500 bg-zinc-50 dark:bg-zinc-900">
                  <tr>
                    <th className="text-left px-2 py-1.5">UID</th>
                    <th className="text-left px-2 py-1.5">Product</th>
                    <th className="text-left px-2 py-1.5">Comp</th>
                    <th className="text-left px-2 py-1.5">Machine</th>
                    <th className="text-right px-2 py-1.5">Before</th>
                    <th className="text-right px-2 py-1.5">After</th>
                    <th className="text-right px-2 py-1.5">Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {report.map((e) => {
                    const delta = ((e.after - e.before) / e.before) * 100;
                    const cls = delta > 0 ? "text-rose-600" : "text-emerald-600";
                    return (
                      <tr
                        key={`${e.unique_id}-${e.component}`}
                        className="border-t border-zinc-100 dark:border-zinc-800"
                      >
                        <td className="px-2 py-1.5 font-mono">{e.unique_id}</td>
                        <td className="px-2 py-1.5">{e.product_name}</td>
                        <td className="px-2 py-1.5 font-mono">{e.component}</td>
                        <td className="px-2 py-1.5 font-mono">{e.machine_number}</td>
                        <td className="px-2 py-1.5 text-right tabular-nums">{e.before}</td>
                        <td className="px-2 py-1.5 text-right tabular-nums">{e.after}</td>
                        <td className={`px-2 py-1.5 text-right tabular-nums ${cls}`}>
                          {delta > 0 ? "+" : ""}
                          {delta.toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {runAfter && (
              <div className="flex items-center justify-end gap-3 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                {ran && <span className="text-xs text-emerald-600">Scheduler ran. See Runs tab.</span>}
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="px-3 py-1.5 rounded-md text-xs border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={handleRunFromReport}
                  disabled={runningScheduler || ran}
                  className="px-4 py-1.5 rounded-md bg-sky-600 text-white text-xs font-medium disabled:opacity-50 hover:bg-sky-700 shadow-sm"
                >
                  {runningScheduler ? "Running…" : ran ? "Ran ✓" : "Run scheduler"}
                </button>
              </div>
            )}
          </div>
        )}
      </FloatingWindow>
    </>
  );
}
