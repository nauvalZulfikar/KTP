import type { MetricsRead, ScheduledAssignmentRead, TaskRead } from "./types";

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const BUSINESS_MIN_PER_DAY = 480;

type Bar = {
  taskId: number;
  product: string;
  component: string;
  machine: string;
  startMs: number;
  endMs: number;
  durationMin: number;
  promisedMs: number;
  orderMs: number;
};

function computeBars(tasks: TaskRead[]): Bar[] {
  const sorted = [...tasks].sort((a, b) => {
    const dA = new Date(a.promised_delivery_date).getTime();
    const dB = new Date(b.promised_delivery_date).getTime();
    if (dA !== dB) return dA - dB;
    if (a.product_name !== b.product_name) return a.product_name.localeCompare(b.product_name);
    return a.component.localeCompare(b.component);
  });
  let globalInHouseEnd = 0;
  const productLastEnd = new Map<string, number>();
  const out: Bar[] = [];
  for (const t of sorted) {
    const orderMs = new Date(t.order_processing_date).getTime();
    const promisedMs = new Date(t.promised_delivery_date).getTime();
    const prev = productLastEnd.get(t.product_name) ?? 0;
    const isOut = t.machine_number === "OutSrc";
    const startMs = isOut
      ? Math.max(orderMs, prev)
      : Math.max(orderMs, prev, globalInHouseEnd);
    const durationMin = (t.quantity_required * t.run_time_per_1000) / 1000;
    const endMs = startMs + (durationMin / BUSINESS_MIN_PER_DAY) * MS_PER_DAY;
    out.push({ taskId: t.id, product: t.product_name, component: t.component, machine: t.machine_number, startMs, endMs, durationMin, promisedMs, orderMs });
    if (!isOut) globalInHouseEnd = endMs;
    productLastEnd.set(t.product_name, endMs);
  }
  return out;
}

export function computeNonPreemptiveMetrics(tasks: TaskRead[]): MetricsRead {
  const bars = computeBars(tasks);

  // Machine utilization
  const machine_utilization: Record<string, number> = {};
  const nonOut = bars.filter((b) => b.machine !== "OutSrc");
  if (nonOut.length > 0) {
    const minStart = Math.min(...nonOut.map((b) => b.startMs));
    const maxEnd = Math.max(...nonOut.map((b) => b.endMs));
    const spanDays = Math.max(1, (maxEnd - minStart) / MS_PER_DAY);
    const capacityMin = spanDays * BUSINESS_MIN_PER_DAY;
    const sumByMachine = new Map<string, number>();
    for (const b of nonOut) sumByMachine.set(b.machine, (sumByMachine.get(b.machine) ?? 0) + b.durationMin);
    for (const [m, total] of sumByMachine) machine_utilization[m] = total / capacityMin;
  }

  // Waiting times
  const compWaitRaw: Record<string, number[]> = {};
  const prodWaitRaw: Record<string, number[]> = {};
  for (const b of bars) {
    const waitDays = (b.startMs - b.orderMs) / MS_PER_DAY;
    (compWaitRaw[b.component] ??= []).push(waitDays);
    (prodWaitRaw[b.product] ??= []).push(waitDays);
  }
  const component_waiting_days: Record<string, number> = {};
  for (const [k, vs] of Object.entries(compWaitRaw)) component_waiting_days[k] = vs.reduce((s, v) => s + v, 0) / vs.length;
  const product_waiting_days: Record<string, number> = {};
  for (const [k, vs] of Object.entries(prodWaitRaw)) product_waiting_days[k] = vs.reduce((s, v) => s + v, 0) / vs.length;

  // Late counts
  const byProduct = new Map<string, number>();
  for (const b of bars) byProduct.set(b.product, Math.max(byProduct.get(b.product) ?? 0, b.endMs));
  const promisedByProduct = new Map<string, number>();
  for (const b of bars) promisedByProduct.set(b.product, b.promisedMs);
  let late = 0;
  let onTime = 0;
  for (const [p, end] of byProduct) {
    if (end > promisedByProduct.get(p)!) late++;
    else onTime++;
  }

  return { machine_utilization, component_waiting_days, product_waiting_days, late_counts: { late, "on time": onTime } };
}

export function computeNonPreemptiveAssignments(tasks: TaskRead[]): ScheduledAssignmentRead[] {
  const bars = computeBars(tasks);
  return bars.map((b, i) => ({
    id: i + 1,
    run_id: 0,
    task_id: b.taskId,
    split_index: 0,
    assigned_quantity: tasks.find((t) => t.id === b.taskId)?.quantity_required ?? 0,
    start_time: new Date(b.startMs).toISOString(),
    end_time: new Date(b.endMs).toISOString(),
  }));
}
