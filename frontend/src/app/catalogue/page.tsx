"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import { fmtJakarta } from "@/lib/datetime";
import type { MetricsRead, ScheduleRunDetail, ScheduleRunRead, TaskRead } from "@/lib/types";

const HISTORY_COUNT = 4;

type RunWithData = {
  run: ScheduleRunRead;
  detail: ScheduleRunDetail | null;
  metrics: MetricsRead | null;
};

export default function CataloguePage() {
  const runs = useSWR<ScheduleRunRead[]>("/runs", fetcher);
  const tasks = useSWR<TaskRead[]>("/tasks", fetcher);
  const [data, setData] = useState<RunWithData[]>([]);
  const [loadingExtra, setLoadingExtra] = useState(false);

  useEffect(() => {
    if (!runs.data) return;
    const latest = runs.data.slice(0, HISTORY_COUNT);
    let cancelled = false;
    setLoadingExtra(true);
    Promise.all(
      latest.map(async (r) => {
        const [detail, metrics] = await Promise.all([
          api.getRun(r.id),
          api.getRunMetrics(r.id),
        ]);
        return { run: r, detail, metrics };
      })
    )
      .then((results) => {
        if (!cancelled) setData(results);
      })
      .finally(() => {
        if (!cancelled) setLoadingExtra(false);
      });
    return () => {
      cancelled = true;
    };
  }, [runs.data]);

  const latestDetail = data[0]?.detail;
  const taskById = new Map<number, TaskRead>();
  for (const t of tasks.data ?? []) taskById.set(t.id, t);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Product Catalogue</h1>

      <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-x-auto">
        <h2 className="text-sm font-medium px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
          Latest scheduled results
          {data[0]?.run && (
            <span className="ml-2 text-xs text-zinc-500">
              Run #{data[0].run.id} · {fmtJakarta(data[0].run.created_at)}
            </span>
          )}
        </h2>
        {!latestDetail ? (
          <div className="p-6 text-sm text-zinc-500">No runs yet.</div>
        ) : (
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
              {[...latestDetail.assignments]
                .sort((a, b) => a.start_time.localeCompare(b.start_time))
                .map((a) => {
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
        )}
      </section>

      <h2 className="text-lg font-medium">Production Scheduling Results — history</h2>
      {loadingExtra && <div className="text-sm text-zinc-500">Loading history…</div>}

      <MetricHistorySection title="Machine Utilization" data={data} extract={(m) => m.machine_utilization} format={(v) => `${(v * 100).toFixed(1)}%`} />
      <MetricHistorySection title="Component Waiting Time" data={data} extract={(m) => m.component_waiting_days} format={(v) => `${v.toFixed(2)}d`} />
      <MetricHistorySection title="Product Waiting Time" data={data} extract={(m) => m.product_waiting_days} format={(v) => `${v.toFixed(2)}d`} />
      <MetricHistorySection title="Late Products" data={data} extract={(m) => m.late_counts} format={(v) => String(v)} />
    </div>
  );
}

function MetricHistorySection({
  title,
  data,
  extract,
  format,
}: {
  title: string;
  data: RunWithData[];
  extract: (m: MetricsRead) => Record<string, number>;
  format: (v: number) => string;
}) {
  const runsWithMetrics = data.filter((d) => d.metrics);
  if (runsWithMetrics.length === 0) return null;

  // Union of keys across all shown runs
  const keys = new Set<string>();
  for (const d of runsWithMetrics) {
    if (d.metrics) for (const k of Object.keys(extract(d.metrics))) keys.add(k);
  }
  const sortedKeys = Array.from(keys).sort();

  return (
    <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-x-auto">
      <h3 className="text-sm font-medium px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">{title}</h3>
      <table className="w-full text-sm">
        <thead className="text-xs uppercase tracking-wide text-zinc-500 bg-zinc-50 dark:bg-zinc-900">
          <tr>
            <th className="text-left px-3 py-2">Key</th>
            {runsWithMetrics.map((d, i) => (
              <th key={d.run.id} className="text-right px-3 py-2">
                {i === 0 ? "Current" : `Version ${i}`}
                <div className="text-[10px] text-zinc-400 font-normal">Run #{d.run.id}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedKeys.map((k) => (
            <tr key={k} className="border-t border-zinc-100 dark:border-zinc-800">
              <td className="px-3 py-2 font-mono">{k}</td>
              {runsWithMetrics.map((d) => {
                const v = d.metrics ? extract(d.metrics)[k] : undefined;
                return (
                  <td key={d.run.id} className="px-3 py-2 text-right font-mono">
                    {v == null ? "—" : format(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
