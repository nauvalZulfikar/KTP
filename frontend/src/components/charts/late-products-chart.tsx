"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

type Props = { data: Record<string, number> };

const COLORS: Record<string, string> = {
  "late": "#ef4444",
  "on time": "#10b981",
};

export function LateProductsChart({ data }: Props) {
  const rows = Object.entries(data).map(([name, count]) => ({ name, count }));
  const total = rows.reduce((s, r) => s + r.count, 0);

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
      <h3 className="text-sm font-medium mb-3">Late Products</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={rows}
              dataKey="count"
              nameKey="name"
              innerRadius={50}
              outerRadius={90}
              label={(entry) => {
                const e = entry as { name?: string; count?: number; value?: number };
                const name = String(e.name ?? "");
                const count = Number(e.count ?? e.value ?? 0);
                return total > 0
                  ? `${name}: ${count} (${Math.round((count / total) * 100)}%)`
                  : name;
              }}
              labelLine={false}
            >
              {rows.map((r, i) => (
                <Cell key={i} fill={COLORS[r.name] ?? "#a1a1aa"} />
              ))}
            </Pie>
            <Tooltip formatter={(v, name) => [`${v} products`, String(name)]} />
            <Legend verticalAlign="bottom" height={28} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
