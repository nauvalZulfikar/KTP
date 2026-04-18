/**
 * Minimal client-side grouped bar chart renderer. Produces a PNG ArrayBuffer
 * suitable for embedding into an .xlsx file via ExcelJS.
 */

type Series = { name: string; color: string; values: (number | null)[] };

export type BarChartInput = {
  title: string;
  categories: string[];
  series: Series[];
  yLabel?: string;
  yFormatter?: (v: number) => string;
};

const WIDTH = 960;
const HEIGHT = 460;
const MARGIN = { top: 50, right: 30, bottom: 80, left: 70 };

export async function renderGroupedBarPng(input: BarChartInput): Promise<ArrayBuffer> {
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("No 2D canvas context");

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  const plotW = WIDTH - MARGIN.left - MARGIN.right;
  const plotH = HEIGHT - MARGIN.top - MARGIN.bottom;

  // Title
  ctx.fillStyle = "#111827";
  ctx.font = "bold 18px sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(input.title, MARGIN.left, 14);

  const rawMax = Math.max(
    0,
    ...input.series.flatMap((s) => s.values.filter((v): v is number => v != null))
  );
  const yMax = rawMax === 0 ? 1 : rawMax * 1.15;
  const yFmt = input.yFormatter ?? ((v: number) => v.toFixed(2));

  // Y axis
  const ticks = 5;
  ctx.strokeStyle = "#e5e7eb";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#6b7280";
  ctx.font = "11px sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= ticks; i++) {
    const y = MARGIN.top + plotH - (plotH * i) / ticks;
    const value = (yMax * i) / ticks;
    ctx.beginPath();
    ctx.moveTo(MARGIN.left, y);
    ctx.lineTo(MARGIN.left + plotW, y);
    ctx.stroke();
    ctx.fillText(yFmt(value), MARGIN.left - 6, y);
  }

  if (input.yLabel) {
    ctx.save();
    ctx.translate(18, MARGIN.top + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = "center";
    ctx.fillStyle = "#374151";
    ctx.font = "12px sans-serif";
    ctx.fillText(input.yLabel, 0, 0);
    ctx.restore();
  }

  // X categories + grouped bars
  const groups = input.categories.length;
  const groupW = plotW / Math.max(1, groups);
  const innerPad = 0.18;
  const seriesCount = input.series.length;
  const barW = (groupW * (1 - innerPad * 2)) / Math.max(1, seriesCount);

  ctx.fillStyle = "#374151";
  ctx.font = "11px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let gi = 0; gi < groups; gi++) {
    const gx = MARGIN.left + groupW * gi;
    const cat = input.categories[gi];
    ctx.save();
    const labelX = gx + groupW / 2;
    const labelY = MARGIN.top + plotH + 8;
    ctx.translate(labelX, labelY);
    ctx.rotate(cat.length > 10 ? -Math.PI / 6 : 0);
    ctx.fillText(cat, 0, 0);
    ctx.restore();

    for (let si = 0; si < seriesCount; si++) {
      const raw = input.series[si].values[gi];
      if (raw == null) continue;
      const h = (raw / yMax) * plotH;
      const x = gx + groupW * innerPad + barW * si;
      const y = MARGIN.top + plotH - h;
      ctx.fillStyle = input.series[si].color;
      ctx.fillRect(x, y, barW - 2, h);
    }
  }

  // Legend (horizontal across top)
  ctx.font = "12px sans-serif";
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  let lx = MARGIN.left;
  const ly = MARGIN.top - 18;
  for (const s of input.series) {
    ctx.fillStyle = s.color;
    ctx.fillRect(lx, ly - 5, 10, 10);
    ctx.fillStyle = "#374151";
    ctx.fillText(s.name, lx + 14, ly);
    lx += 14 + ctx.measureText(s.name).width + 18;
  }

  // X axis line
  ctx.strokeStyle = "#9ca3af";
  ctx.beginPath();
  ctx.moveTo(MARGIN.left, MARGIN.top + plotH);
  ctx.lineTo(MARGIN.left + plotW, MARGIN.top + plotH);
  ctx.stroke();

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob((b) => resolve(b), "image/png")
  );
  if (!blob) throw new Error("Failed to encode PNG");
  return await blob.arrayBuffer();
}

// =====================================================================
// Gantt chart renderer
// =====================================================================

type GanttBar = {
  product: string;
  component: string;
  machine: string;
  startMs: number;
  endMs: number;
  outsource: boolean;
};

export type GanttChartInput = {
  title: string;
  bars: GanttBar[];
};

const COMPONENT_COLORS: Record<string, string> = {
  C1: "#3b82f6",
  C2: "#10b981",
  C3: "#f59e0b",
  C4: "#ef4444",
  C5: "#8b5cf6",
  C6: "#06b6d4",
};
const COMP_FALLBACK = ["#84cc16", "#ec4899", "#6366f1", "#f97316", "#14b8a6", "#d946ef"];

function compColor(c: string): string {
  if (COMPONENT_COLORS[c]) return COMPONENT_COLORS[c];
  let h = 0;
  for (let i = 0; i < c.length; i++) h = (h * 31 + c.charCodeAt(i)) | 0;
  return COMP_FALLBACK[Math.abs(h) % COMP_FALLBACK.length];
}

const GANTT_W = 1100;
const GANTT_MARGIN = { top: 50, right: 20, bottom: 60, left: 100 };
const BAR_H = 22;
const LABEL_H = 12;
const ROW_H = BAR_H + LABEL_H + 4;

export async function renderGanttPng(input: GanttChartInput): Promise<ArrayBuffer> {
  const { bars, title } = input;
  if (bars.length === 0) {
    // Empty placeholder
    const c = document.createElement("canvas");
    c.width = 400; c.height = 60;
    const x = c.getContext("2d")!;
    x.fillStyle = "#fff"; x.fillRect(0, 0, 400, 60);
    x.fillStyle = "#999"; x.font = "14px sans-serif"; x.fillText("No data", 160, 35);
    const b = await new Promise<Blob | null>(r => c.toBlob(r, "image/png"));
    return (await b!.arrayBuffer());
  }

  const products = Array.from(new Set(bars.map(b => b.product))).sort();

  // Assign lanes per product (for overlapping bars)
  type LaneBar = GanttBar & { lane: number };
  const lanedBars: LaneBar[] = [];
  const lanesPerProduct = new Map<string, number>();
  for (const p of products) {
    const pBars = bars.filter(b => b.product === p).sort((a, b) => a.startMs - b.startMs);
    const laneEnds: number[] = [];
    for (const bar of pBars) {
      let lane = -1;
      for (let i = 0; i < laneEnds.length; i++) {
        if (laneEnds[i] <= bar.startMs) { lane = i; laneEnds[i] = bar.endMs; break; }
      }
      if (lane === -1) { lane = laneEnds.length; laneEnds.push(bar.endMs); }
      lanedBars.push({ ...bar, lane });
    }
    lanesPerProduct.set(p, Math.max(1, laneEnds.length));
  }

  // Compute row Y positions
  const rowY = new Map<string, number>();
  const rowH = new Map<string, number>();
  let y = GANTT_MARGIN.top;
  for (const p of products) {
    const lanes = lanesPerProduct.get(p) ?? 1;
    const h = lanes * ROW_H;
    rowY.set(p, y);
    rowH.set(p, h);
    y += h;
  }
  const totalH = y + GANTT_MARGIN.bottom;

  const minMs = Math.min(...bars.map(b => b.startMs));
  const maxMs = Math.max(...bars.map(b => b.endMs));
  const range = Math.max(1, maxMs - minMs);
  const plotW = GANTT_W - GANTT_MARGIN.left - GANTT_MARGIN.right;

  const canvas = document.createElement("canvas");
  canvas.width = GANTT_W;
  canvas.height = totalH;
  const ctx = canvas.getContext("2d")!;

  // Background
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, GANTT_W, totalH);

  // Title
  ctx.fillStyle = "#111827";
  ctx.font = "bold 16px sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(title, GANTT_MARGIN.left, 12);

  // Weekly ticks
  const msPerWeek = 7 * 24 * 60 * 60 * 1000;
  const startDate = new Date(minMs);
  startDate.setHours(0, 0, 0, 0);
  const dow = startDate.getDay();
  startDate.setDate(startDate.getDate() + (dow === 0 ? -6 : 1 - dow));
  ctx.strokeStyle = "#e5e7eb";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#6b7280";
  ctx.font = "10px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let t = startDate.getTime(); t <= maxMs + msPerWeek; t += msPerWeek) {
    const x = GANTT_MARGIN.left + ((t - minMs) / range) * plotW;
    if (x < GANTT_MARGIN.left - 10 || x > GANTT_W - GANTT_MARGIN.right + 10) continue;
    ctx.beginPath();
    ctx.moveTo(x, GANTT_MARGIN.top);
    ctx.lineTo(x, totalH - GANTT_MARGIN.bottom);
    ctx.stroke();
    const d = new Date(t);
    ctx.fillText(
      d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      x, totalH - GANTT_MARGIN.bottom + 6
    );
  }

  // Row backgrounds & product labels
  ctx.font = "11px sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i < products.length; i++) {
    const p = products[i];
    const ry = rowY.get(p)!;
    const rh = rowH.get(p)!;
    if (i % 2 === 1) {
      ctx.fillStyle = "#f9fafb";
      ctx.fillRect(GANTT_MARGIN.left, ry, plotW, rh);
    }
    // Row separator
    ctx.strokeStyle = "#e5e7eb";
    ctx.beginPath();
    ctx.moveTo(GANTT_MARGIN.left, ry + rh);
    ctx.lineTo(GANTT_W - GANTT_MARGIN.right, ry + rh);
    ctx.stroke();
    // Label
    ctx.fillStyle = "#374151";
    ctx.fillText(p, GANTT_MARGIN.left - 8, ry + rh / 2);
  }

  // Draw bars
  for (const b of lanedBars) {
    const ry = rowY.get(b.product)!;
    const x1 = GANTT_MARGIN.left + ((b.startMs - minMs) / range) * plotW;
    const x2 = GANTT_MARGIN.left + ((b.endMs - minMs) / range) * plotW;
    const bw = Math.max(2, x2 - x1);
    const by = ry + b.lane * ROW_H + 2;
    const color = compColor(b.component);

    ctx.fillStyle = color;
    ctx.fillRect(x1, by, bw, BAR_H);

    // Outsource stripes
    if (b.outsource) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(x1, by, bw, BAR_H);
      ctx.clip();
      ctx.strokeStyle = "rgba(255,255,255,0.4)";
      ctx.lineWidth = 2;
      for (let sx = x1 - BAR_H; sx < x1 + bw + BAR_H; sx += 8) {
        ctx.beginPath();
        ctx.moveTo(sx, by + BAR_H);
        ctx.lineTo(sx + BAR_H, by);
        ctx.stroke();
      }
      ctx.restore();
    }

    // Border
    ctx.strokeStyle = "rgba(0,0,0,0.2)";
    ctx.lineWidth = 1;
    ctx.strokeRect(x1, by, bw, BAR_H);

    // Machine label underneath (not on outsource bars)
    if (!b.outsource) {
      ctx.fillStyle = "#6b7280";
      ctx.font = "8px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(b.machine, x1 + bw / 2, by + BAR_H + 1);
    }
  }

  // Legend
  const components = Array.from(new Set(bars.map(b => b.component))).sort();
  ctx.font = "11px sans-serif";
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  let lx = GANTT_MARGIN.left;
  const ly = GANTT_MARGIN.top - 16;
  for (const c of components) {
    ctx.fillStyle = compColor(c);
    ctx.fillRect(lx, ly - 5, 10, 10);
    ctx.fillStyle = "#374151";
    ctx.fillText(c, lx + 13, ly);
    lx += 13 + ctx.measureText(c).width + 14;
  }
  // OutSrc legend
  ctx.fillStyle = "#71717a";
  ctx.fillRect(lx, ly - 5, 14, 10);
  ctx.save();
  ctx.beginPath();
  ctx.rect(lx, ly - 5, 14, 10);
  ctx.clip();
  ctx.strokeStyle = "rgba(255,255,255,0.5)";
  ctx.lineWidth = 1.5;
  for (let sx = lx - 10; sx < lx + 24; sx += 5) {
    ctx.beginPath(); ctx.moveTo(sx, ly + 5); ctx.lineTo(sx + 10, ly - 5); ctx.stroke();
  }
  ctx.restore();
  ctx.fillStyle = "#374151";
  ctx.fillText("OutSrc", lx + 18, ly);

  const blob = await new Promise<Blob | null>(r => canvas.toBlob(r, "image/png"));
  if (!blob) throw new Error("Failed to encode Gantt PNG");
  return await blob.arrayBuffer();
}
