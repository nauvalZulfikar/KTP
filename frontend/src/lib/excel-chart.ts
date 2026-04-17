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
