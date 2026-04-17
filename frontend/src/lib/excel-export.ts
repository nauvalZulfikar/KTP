import ExcelJS from "exceljs";
import { api } from "./api";
import { renderGroupedBarPng } from "./excel-chart";
import type { MetricsRead, ScheduleRunDetail, ScheduleRunRead, TaskRead } from "./types";

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const BUSINESS_MIN_PER_DAY = 480;
const HISTORY_COUNT = 4;

const SERIES_PALETTE = [
  "#3b82f6", // no MSJS
  "#10b981", // run current
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
];

type NoMsjsBar = {
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

function computeNoMsjs(tasks: TaskRead[]): NoMsjsBar[] {
  const sorted = [...tasks].sort((a, b) => {
    const dA = new Date(a.promised_delivery_date).getTime();
    const dB = new Date(b.promised_delivery_date).getTime();
    if (dA !== dB) return dA - dB;
    if (a.product_name !== b.product_name) return a.product_name.localeCompare(b.product_name);
    return a.component.localeCompare(b.component);
  });
  const machineLastEnd = new Map<string, number>();
  const productLastEnd = new Map<string, number>();
  const out: NoMsjsBar[] = [];
  for (const t of sorted) {
    const orderMs = new Date(t.order_processing_date).getTime();
    const promisedMs = new Date(t.promised_delivery_date).getTime();
    const prev = productLastEnd.get(t.product_name) ?? 0;
    const isOut = t.machine_number === "OutSrc";
    const mEnd = isOut ? 0 : machineLastEnd.get(t.machine_number) ?? 0;
    const startMs = Math.max(orderMs, prev, mEnd);
    const durationMin = (t.quantity_required * t.run_time_per_1000) / 1000;
    const endMs = startMs + (durationMin / BUSINESS_MIN_PER_DAY) * MS_PER_DAY;
    out.push({
      taskId: t.id,
      product: t.product_name,
      component: t.component,
      machine: t.machine_number,
      startMs,
      endMs,
      durationMin,
      promisedMs,
      orderMs,
    });
    if (!isOut) machineLastEnd.set(t.machine_number, endMs);
    productLastEnd.set(t.product_name, endMs);
  }
  return out;
}

type NoMsjsMetrics = {
  machineUtil: Record<string, number>;
  componentWaiting: Record<string, number>;
  productWaiting: Record<string, number>;
  lateCounts: Record<string, number>;
};

function computeNoMsjsMetrics(bars: NoMsjsBar[]): NoMsjsMetrics {
  const machineUtil: Record<string, number> = {};
  const componentWaitRaw: Record<string, number[]> = {};
  const productWaitRaw: Record<string, number[]> = {};

  const nonOut = bars.filter((b) => b.machine !== "OutSrc");
  if (nonOut.length > 0) {
    const minStart = Math.min(...nonOut.map((b) => b.startMs));
    const maxEnd = Math.max(...nonOut.map((b) => b.endMs));
    const spanDays = Math.max(1, (maxEnd - minStart) / MS_PER_DAY);
    const capacityMin = spanDays * BUSINESS_MIN_PER_DAY;
    const sumByMachine = new Map<string, number>();
    for (const b of nonOut) {
      sumByMachine.set(b.machine, (sumByMachine.get(b.machine) ?? 0) + b.durationMin);
    }
    for (const [m, total] of sumByMachine) {
      machineUtil[m] = total / capacityMin;
    }
  }

  for (const b of bars) {
    const waitDays = (b.startMs - b.orderMs) / MS_PER_DAY;
    (componentWaitRaw[b.component] ??= []).push(waitDays);
    (productWaitRaw[b.product] ??= []).push(waitDays);
  }

  const componentWaiting: Record<string, number> = {};
  for (const [k, vs] of Object.entries(componentWaitRaw)) {
    componentWaiting[k] = vs.reduce((s, v) => s + v, 0) / vs.length;
  }
  const productWaiting: Record<string, number> = {};
  for (const [k, vs] of Object.entries(productWaitRaw)) {
    productWaiting[k] = vs.reduce((s, v) => s + v, 0) / vs.length;
  }

  const byProduct = new Map<string, number>();
  for (const b of bars) {
    byProduct.set(b.product, Math.max(byProduct.get(b.product) ?? 0, b.endMs));
  }
  const promisedByProduct = new Map<string, number>();
  for (const b of bars) promisedByProduct.set(b.product, b.promisedMs);
  let late = 0;
  let onTime = 0;
  for (const [p, end] of byProduct) {
    const prom = promisedByProduct.get(p)!;
    if (end > prom) late++;
    else onTime++;
  }
  return {
    machineUtil,
    componentWaiting,
    productWaiting,
    lateCounts: { late, "on time": onTime },
  };
}

type RunBundle = { run: ScheduleRunRead; detail: ScheduleRunDetail; metrics: MetricsRead };

function iso(ms: number): string {
  const d = new Date(ms);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

function setHeaderRow(sheet: ExcelJS.Worksheet, headers: string[]) {
  sheet.addRow(headers);
  const row = sheet.getRow(sheet.rowCount);
  row.font = { bold: true };
  row.fill = {
    type: "pattern",
    pattern: "solid",
    fgColor: { argb: "FFF3F4F6" },
  };
}

export async function exportToExcel(): Promise<void> {
  const [originalTasks, dbTasks, runs] = await Promise.all([
    api.listOriginalTasks(),
    api.listTasks(),
    api.listRuns(),
  ]);
  const recentRuns = runs.slice(0, HISTORY_COUNT);
  const bundles: RunBundle[] = await Promise.all(
    recentRuns.map(async (r) => {
      const [detail, metrics] = await Promise.all([api.getRun(r.id), api.getRunMetrics(r.id)]);
      return { run: r, detail, metrics };
    })
  );

  const wb = new ExcelJS.Workbook();
  wb.created = new Date();

  // =================================================================
  // Sheet 1 — No MSJS
  // =================================================================
  const noMsjsBars = computeNoMsjs(originalTasks);
  const sheetNo = wb.addWorksheet("No MSJS");
  setHeaderRow(sheetNo, [
    "Task ID", "Product", "Component", "Machine",
    "Quantity", "Run/1000 (min)", "Duration (min)",
    "Order Date", "Promised Date", "Start", "End",
  ]);
  const taskById = new Map<number, TaskRead>();
  for (const t of originalTasks) taskById.set(t.id, t);
  for (const b of noMsjsBars) {
    const t = taskById.get(b.taskId);
    sheetNo.addRow([
      b.taskId,
      b.product,
      b.component,
      b.machine,
      t?.quantity_required ?? "",
      t?.run_time_per_1000 ?? "",
      b.durationMin.toFixed(1),
      iso(b.orderMs),
      iso(b.promisedMs),
      iso(b.startMs),
      iso(b.endMs),
    ]);
  }
  sheetNo.columns.forEach((c) => (c.width = 16));

  // =================================================================
  // Sheet 2 — With MSJS (latest run)
  // =================================================================
  const sheetWith = wb.addWorksheet("With MSJS");
  if (bundles.length > 0) {
    const latest = bundles[0];
    const dbTaskById = new Map<number, TaskRead>();
    for (const t of dbTasks) dbTaskById.set(t.id, t);
    sheetWith.addRow([
      `Latest scheduled run #${latest.run.id} (${iso(new Date(latest.run.created_at).getTime())})`,
    ]);
    sheetWith.getRow(1).font = { bold: true };
    sheetWith.addRow([]);
    setHeaderRow(sheetWith, [
      "Assignment ID", "Task ID", "Product", "Component", "Machine",
      "Split #", "Quantity", "Start", "End",
    ]);
    const sorted = [...latest.detail.assignments].sort((a, b) =>
      a.start_time.localeCompare(b.start_time)
    );
    for (const a of sorted) {
      const t = dbTaskById.get(a.task_id);
      sheetWith.addRow([
        a.id,
        a.task_id,
        t?.product_name ?? "",
        t?.component ?? "",
        t?.machine_number ?? "",
        a.split_index,
        a.assigned_quantity,
        iso(new Date(a.start_time).getTime()),
        iso(new Date(a.end_time).getTime()),
      ]);
    }
  } else {
    sheetWith.addRow(["No runs yet. Click 'Run scheduler' first."]);
  }
  sheetWith.columns.forEach((c) => (c.width = 18));

  // =================================================================
  // Metric sheets (table + chart). Columns: key | No MSJS | Run N ... Run N-3
  // =================================================================
  const noMsjsMetrics = computeNoMsjsMetrics(noMsjsBars);

  type MetricDef = {
    title: string;
    keyLabel: string;
    format: (v: number) => string;
    yLabel: string;
    yFormat: (v: number) => string;
    noMsjs: Record<string, number>;
    perRun: (m: MetricsRead) => Record<string, number>;
    asPct?: boolean;
  };

  const metricDefs: MetricDef[] = [
    {
      title: "Machine Utilization",
      keyLabel: "Machine",
      format: (v) => `${(v * 100).toFixed(1)}%`,
      yLabel: "Utilization",
      yFormat: (v) => `${(v * 100).toFixed(0)}%`,
      noMsjs: noMsjsMetrics.machineUtil,
      perRun: (m) => m.machine_utilization,
      asPct: true,
    },
    {
      title: "Component Waiting Time",
      keyLabel: "Component",
      format: (v) => `${v.toFixed(2)} days`,
      yLabel: "Days",
      yFormat: (v) => `${v.toFixed(1)}d`,
      noMsjs: noMsjsMetrics.componentWaiting,
      perRun: (m) => m.component_waiting_days,
    },
    {
      title: "Product Waiting Time",
      keyLabel: "Product",
      format: (v) => `${v.toFixed(2)} days`,
      yLabel: "Days",
      yFormat: (v) => `${v.toFixed(1)}d`,
      noMsjs: noMsjsMetrics.productWaiting,
      perRun: (m) => m.product_waiting_days,
    },
    {
      title: "Late Products",
      keyLabel: "Status",
      format: (v) => String(v),
      yLabel: "Count",
      yFormat: (v) => v.toFixed(0),
      noMsjs: noMsjsMetrics.lateCounts,
      perRun: (m) => m.late_counts,
    },
  ];

  for (const def of metricDefs) {
    const sheet = wb.addWorksheet(def.title);

    // Collect all keys across No MSJS and each run
    const keySet = new Set<string>();
    for (const k of Object.keys(def.noMsjs)) keySet.add(k);
    for (const b of bundles) for (const k of Object.keys(def.perRun(b.metrics))) keySet.add(k);
    const keys = Array.from(keySet).sort();

    const runHeaders = bundles.map((b, i) => (i === 0 ? `Run #${b.run.id} (current)` : `Run #${b.run.id}`));
    setHeaderRow(sheet, [def.keyLabel, "No MSJS", ...runHeaders]);

    for (const k of keys) {
      const row: (string | number)[] = [k];
      const noVal = def.noMsjs[k];
      row.push(noVal == null ? "" : def.format(noVal));
      for (const b of bundles) {
        const v = def.perRun(b.metrics)[k];
        row.push(v == null ? "" : def.format(v));
      }
      sheet.addRow(row);
    }
    sheet.columns.forEach((c) => (c.width = 20));

    // Build chart data
    const seriesList = [
      {
        name: "No MSJS",
        color: SERIES_PALETTE[0],
        values: keys.map((k) => def.noMsjs[k] ?? null),
      },
      ...bundles.map((b, i) => ({
        name: i === 0 ? `Run #${b.run.id} (current)` : `Run #${b.run.id}`,
        color: SERIES_PALETTE[(i + 1) % SERIES_PALETTE.length],
        values: keys.map((k) => def.perRun(b.metrics)[k] ?? null),
      })),
    ];

    const pngBuffer = await renderGroupedBarPng({
      title: `${def.title} — No MSJS vs runs`,
      categories: keys,
      series: seriesList,
      yLabel: def.yLabel,
      yFormatter: def.yFormat,
    });

    const imageId = wb.addImage({
      buffer: pngBuffer,
      extension: "png",
    });
    const imageRow = sheet.rowCount + 2;
    sheet.addImage(imageId, {
      tl: { col: 0, row: imageRow },
      ext: { width: 960, height: 460 },
    });
  }

  // =================================================================
  // Download
  // =================================================================
  const buffer = await wb.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-T:]/g, "");
  a.download = `machine-scheduler-${stamp}.xlsx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
