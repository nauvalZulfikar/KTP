"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TaskRead } from "@/lib/types";

type Props = { tasks: TaskRead[] };

const PALETTE = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#84cc16", "#ec4899",
];

export function UnscheduledDurationChart({ tasks }: Props) {
  const { rows, components } = useMemo(() => {
    const components = Array.from(new Set(tasks.map((t) => t.component))).sort();
    const byProduct = new Map<string, Record<string, number>>();
    for (const t of tasks) {
      const duration = (t.quantity_required * t.run_time_per_1000) / 1000;
      const bucket = byProduct.get(t.product_name) ?? {};
      bucket[t.component] = (bucket[t.component] ?? 0) + duration;
      byProduct.set(t.product_name, bucket);
    }
    const rows = Array.from(byProduct.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([product, comps]) => ({ product, ...comps }));
    return { rows, components };
  }, [tasks]);

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
      <h3 className="text-sm font-medium mb-3">
        Unscheduled Duration <span className="text-xs text-zinc-500">(raw minutes per product, stacked by component)</span>
      </h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 24, bottom: 8, left: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}m`} />
            <YAxis type="category" dataKey="product" tick={{ fontSize: 12 }} width={80} />
            <Tooltip formatter={(v) => `${Math.round(Number(v))} min`} />
            <Legend verticalAlign="bottom" height={24} />
            {components.map((c, i) => (
              <Bar key={c} dataKey={c} stackId="dur" fill={PALETTE[i % PALETTE.length]} radius={0}>
                {rows.map((_, ri) => (
                  <Cell key={ri} />
                ))}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
