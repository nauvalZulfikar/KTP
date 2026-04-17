import type { MetricsRead } from "@/lib/types";

type Props = { metrics: MetricsRead };

function pct(n: number): string {
  return `${(n * 100).toFixed(0)}%`;
}

function days(n: number): string {
  return `${n.toFixed(2)}d`;
}

export function MetricsTiles({ metrics }: Props) {
  const machines = Object.entries(metrics.machine_utilization).sort(([a], [b]) =>
    a.localeCompare(b)
  );
  const late = metrics.late_counts.late ?? 0;
  const onTime = metrics.late_counts["on time"] ?? 0;
  const total = late + onTime;
  const onTimeRate = total > 0 ? onTime / total : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
        <div className="text-xs uppercase tracking-wide text-zinc-500">On-time rate</div>
        <div className="mt-1 text-2xl font-semibold">{pct(onTimeRate)}</div>
        <div className="text-xs text-zinc-500 mt-1">
          {onTime} on time · {late} late · {total} total
        </div>
      </div>

      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
        <div className="text-xs uppercase tracking-wide text-zinc-500">Machine utilization</div>
        <div className="mt-2 space-y-1">
          {machines.length === 0 ? (
            <div className="text-sm text-zinc-500">—</div>
          ) : (
            machines.map(([m, u]) => (
              <div key={m} className="flex justify-between text-sm">
                <span className="font-mono">{m}</span>
                <span>{pct(u)}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
        <div className="text-xs uppercase tracking-wide text-zinc-500">Avg product wait</div>
        <div className="mt-2 space-y-1">
          {Object.entries(metrics.product_waiting_days)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5)
            .map(([p, d]) => (
              <div key={p} className="flex justify-between text-sm">
                <span className="truncate mr-2">{p}</span>
                <span>{days(d)}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
