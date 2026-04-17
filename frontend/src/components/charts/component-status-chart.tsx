"use client";

import { useMemo } from "react";
import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { ScheduledAssignmentRead, TaskRead } from "@/lib/types";

type Props = {
  assignments: ScheduledAssignmentRead[];
  tasks: TaskRead[];
};

type Point = {
  product: string;
  component: string;
  machine: string;
  status: "InProgress" | "Completed" | "Late";
  outsource: boolean;
};

const STATUS_COLORS: Record<Point["status"], string> = {
  InProgress: "#f59e0b",
  Completed: "#10b981",
  Late: "#ef4444",
};

export function ComponentStatusChart({ assignments, tasks }: Props) {
  const points = useMemo<Point[]>(() => {
    const assignmentsByTask = new Map<number, ScheduledAssignmentRead[]>();
    for (const a of assignments) {
      const list = assignmentsByTask.get(a.task_id) ?? [];
      list.push(a);
      assignmentsByTask.set(a.task_id, list);
    }
    return tasks.map((t) => {
      const as = assignmentsByTask.get(t.id) ?? [];
      const promised = new Date(t.promised_delivery_date).getTime();
      let status: Point["status"] = "InProgress";
      if (as.length > 0) {
        const finalEnd = Math.max(...as.map((x) => new Date(x.end_time).getTime()));
        status = finalEnd > promised ? "Late" : "Completed";
      }
      return {
        product: t.product_name,
        component: t.component,
        machine: t.machine_number,
        status,
        outsource: t.machine_number === "OutSrc" || t.process_type === "Outsource",
      };
    });
  }, [assignments, tasks]);

  const products = useMemo(
    () => Array.from(new Set(points.map((p) => p.product))).sort(),
    [points]
  );
  const components = useMemo(
    () => Array.from(new Set(points.map((p) => p.component))).sort(),
    [points]
  );

  const productIndex = (p: string) => products.indexOf(p);
  const componentIndex = (c: string) => components.indexOf(c);

  const byStatus: Record<Point["status"], { x: number; y: number; product: string; component: string; machine: string; shape: "circle" | "square" }[]> = {
    InProgress: [],
    Completed: [],
    Late: [],
  };
  for (const p of points) {
    byStatus[p.status].push({
      x: productIndex(p.product),
      y: componentIndex(p.component),
      product: p.product,
      component: p.component,
      machine: p.machine,
      shape: p.outsource ? "circle" : "square",
    });
  }

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4">
      <h3 className="text-sm font-medium mb-3">
        Product / Component Status
        <span className="ml-2 text-xs text-zinc-500">
          (● outsource, ■ in-house · color = status)
        </span>
      </h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 24, bottom: 16, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[-0.5, products.length - 0.5]}
              ticks={products.map((_, i) => i)}
              tickFormatter={(i: number) => products[i] ?? ""}
              tick={{ fontSize: 11 }}
              angle={-20}
              textAnchor="end"
              interval={0}
              height={50}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[-0.5, components.length - 0.5]}
              ticks={components.map((_, i) => i)}
              tickFormatter={(i: number) => components[i] ?? ""}
              tick={{ fontSize: 11 }}
              interval={0}
            />
            <ZAxis range={[120, 120]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as { product: string; component: string; machine: string };
                return (
                  <div className="rounded bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 px-2 py-1 text-xs shadow">
                    <div className="font-medium">{p.product} · {p.component}</div>
                    <div className="text-zinc-500">Machine: {p.machine}</div>
                  </div>
                );
              }}
            />
            <Legend verticalAlign="bottom" height={24} iconType="circle" />
            <Scatter name="Completed" data={byStatus.Completed} fill={STATUS_COLORS.Completed} shape="square" />
            <Scatter name="Late" data={byStatus.Late} fill={STATUS_COLORS.Late} shape="square" />
            <Scatter name="InProgress" data={byStatus.InProgress} fill={STATUS_COLORS.InProgress} shape="square" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
