"use client";

import { use } from "react";
import useSWR from "swr";
import { MetricsTiles } from "@/components/metrics-tiles";
import { fetcher } from "@/lib/api";
import { fmtJakarta } from "@/lib/datetime";
import type { MetricsRead, ScheduleRunDetail, TaskRead } from "@/lib/types";

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const run = useSWR<ScheduleRunDetail>(`/runs/${id}`, fetcher);
  const metrics = useSWR<MetricsRead>(`/runs/${id}/metrics`, fetcher);
  const tasks = useSWR<TaskRead[]>("/tasks", fetcher);

  const taskById = new Map<number, TaskRead>();
  for (const t of tasks.data ?? []) taskById.set(t.id, t);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Run #{id}</h1>
        {run.data && (
          <p className="text-sm text-zinc-500">
            {fmtJakarta(run.data.created_at)}
            {run.data.notes ? ` — ${run.data.notes}` : ""}
          </p>
        )}
      </div>

      {metrics.data && <MetricsTiles metrics={metrics.data} />}

      {run.data && (
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase tracking-wide text-zinc-500 bg-zinc-50 dark:bg-zinc-900">
              <tr>
                <th className="text-left px-3 py-2">Product</th>
                <th className="text-left px-3 py-2">Comp</th>
                <th className="text-left px-3 py-2">Machine</th>
                <th className="text-right px-3 py-2">Qty</th>
                <th className="text-left px-3 py-2">Start</th>
                <th className="text-left px-3 py-2">End</th>
              </tr>
            </thead>
            <tbody>
              {run.data.assignments.map((a) => {
                const t = taskById.get(a.task_id);
                return (
                  <tr key={a.id} className="border-t border-zinc-100 dark:border-zinc-800">
                    <td className="px-3 py-2">{t?.product_name ?? `#${a.task_id}`}</td>
                    <td className="px-3 py-2 font-mono">{t?.component ?? "—"}</td>
                    <td className="px-3 py-2 font-mono">{t?.machine_number ?? "—"}</td>
                    <td className="px-3 py-2 text-right">{a.assigned_quantity.toLocaleString()}</td>
                    <td className="px-3 py-2 text-xs">{new Date(a.start_time).toLocaleString()}</td>
                    <td className="px-3 py-2 text-xs">{new Date(a.end_time).toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
