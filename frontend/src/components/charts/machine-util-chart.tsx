"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Props = { data: Record<string, number> };

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"];

export function MachineUtilChart({ data }: Props) {
  const rows = Object.entries(data)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([machine, util]) => ({ machine, pct: Math.round(util * 1000) / 10 }));

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
      <h3 className="text-sm font-medium mb-3">Machine Utilisation</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 24, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
            <XAxis dataKey="machine" tick={{ fontSize: 12 }} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(v: number) => `${v}%`}
              domain={[0, 100]}
            />
            <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
            <Bar dataKey="pct" radius={[6, 6, 0, 0]}>
              <LabelList dataKey="pct" position="top" formatter={(v) => `${Number(v).toFixed(1)}%`} style={{ fontSize: 11, fill: "#52525b" }} />
              {rows.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
