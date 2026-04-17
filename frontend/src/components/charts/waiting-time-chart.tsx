"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Props = {
  title: string;
  data: Record<string, number>;
  xLabel: string;
  palette?: string[];
};

const DEFAULT_PALETTE = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#84cc16", "#ec4899",
];

export function WaitingTimeChart({ title, data, xLabel, palette = DEFAULT_PALETTE }: Props) {
  const rows = Object.entries(data)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, days]) => ({ name, days: Math.round(days * 100) / 100 }));

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
      <h3 className="text-sm font-medium mb-3">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 24, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} label={{ value: xLabel, position: "insideBottom", offset: -2, fontSize: 11 }} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(v: number) => `${v}d`}
            />
            <Tooltip formatter={(v) => `${Number(v).toFixed(2)} days`} />
            <Bar dataKey="days" radius={[6, 6, 0, 0]}>
              <LabelList dataKey="days" position="top" formatter={(v) => `${Number(v).toFixed(2)}d`} style={{ fontSize: 11, fill: "#52525b" }} />
              {rows.map((_, i) => (
                <Cell key={i} fill={palette[i % palette.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
