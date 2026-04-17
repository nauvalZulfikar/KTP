"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { TaskRead, TaskUpdate } from "@/lib/types";

const NUMBER_FIELDS = new Set([
  "quantity_required",
  "run_time_per_1000",
  "cycle_time_seconds",
  "setup_time_seconds",
  "sr_no",
]);
const DATE_FIELDS = new Set(["order_processing_date", "promised_delivery_date"]);
const EDITABLE_FIELDS = [
  "product_name",
  "component",
  "operation",
  "process_type",
  "machine_number",
  "quantity_required",
  "run_time_per_1000",
  "cycle_time_seconds",
  "setup_time_seconds",
  "sr_no",
  "order_processing_date",
  "promised_delivery_date",
  "status",
] as const;

type Field = (typeof EDITABLE_FIELDS)[number];

function EditSection({
  heading,
  processTypeFilter,
  tasks,
  onSaved,
}: {
  heading: string;
  processTypeFilter: (t: TaskRead) => boolean;
  tasks: TaskRead[];
  onSaved: () => Promise<void>;
}) {
  const filtered = tasks.filter(processTypeFilter);
  const products = useMemo(
    () => Array.from(new Set(filtered.map((t) => t.product_name))).sort(),
    [filtered]
  );
  const [product, setProduct] = useState<string>("");
  const components = useMemo(() => {
    const subset = filtered.filter((t) => t.product_name === product);
    return Array.from(new Set(subset.map((t) => t.component))).sort();
  }, [filtered, product]);
  const [component, setComponent] = useState<string>("");
  const [field, setField] = useState<Field>("quantity_required");
  const [value, setValue] = useState<string>("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const target = filtered.find(
    (t) => t.product_name === product && t.component === component
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    if (!target) {
      setErr("Pick a product and component first.");
      return;
    }
    const body: TaskUpdate = {};
    try {
      if (NUMBER_FIELDS.has(field)) {
        (body as Record<string, unknown>)[field] = Number(value);
      } else if (DATE_FIELDS.has(field)) {
        (body as Record<string, unknown>)[field] = new Date(value).toISOString();
      } else {
        (body as Record<string, unknown>)[field] = value;
      }
      setSaving(true);
      await api.updateTask(target.id, body);
      await onSaved();
      setMsg(`Updated ${field} on ${product} / ${component}.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  const inputType = NUMBER_FIELDS.has(field)
    ? "number"
    : DATE_FIELDS.has(field)
    ? "date"
    : "text";

  return (
    <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3">
      <h2 className="text-base font-medium">{heading}</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
        <label className="flex flex-col text-xs gap-1">
          Product
          <select
            value={product}
            onChange={(e) => {
              setProduct(e.target.value);
              setComponent("");
            }}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          >
            <option value="">—</option>
            {products.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs gap-1">
          Component
          <select
            value={component}
            onChange={(e) => setComponent(e.target.value)}
            disabled={!product}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm disabled:opacity-50"
          >
            <option value="">—</option>
            {components.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs gap-1">
          Field
          <select
            value={field}
            onChange={(e) => setField(e.target.value as Field)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          >
            {EDITABLE_FIELDS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs gap-1">
          New value
          <input
            type={inputType}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
            required
          />
        </label>
        <div className="md:col-span-4 flex items-center gap-3">
          <button
            type="submit"
            disabled={saving || !target}
            className="px-4 py-1.5 rounded-md bg-sky-600 text-white text-xs font-medium disabled:opacity-50 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-400 shadow-sm"
          >
            {saving ? "Saving…" : "Confirm"}
          </button>
          {msg && <span className="text-xs text-emerald-600">{msg}</span>}
          {err && <span className="text-xs text-red-600">{err}</span>}
        </div>
      </form>

      {target && (
        <div className="mt-3 text-xs text-zinc-600 dark:text-zinc-400 font-mono border-t border-zinc-100 dark:border-zinc-800 pt-3">
          <div className="font-semibold text-zinc-800 dark:text-zinc-200 mb-1">Current row</div>
          <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(target, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}

function TimeConverter() {
  const [mode, setMode] = useState<"d2m" | "h2m" | "m2d">("d2m");
  const [input, setInput] = useState<string>("0");
  const v = Number(input) || 0;
  let out = "";
  if (mode === "d2m") out = `${v * 24 * 60} minutes`;
  if (mode === "h2m") out = `${v * 60} minutes`;
  if (mode === "m2d") out = `${(v / (24 * 60)).toFixed(6)} days`;
  return (
    <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3">
      <h2 className="text-base font-medium">Time Converter</h2>
      <div className="flex gap-3 items-end flex-wrap">
        <label className="flex flex-col text-xs gap-1">
          Conversion
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as "d2m" | "h2m" | "m2d")}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          >
            <option value="d2m">Days → Minutes</option>
            <option value="h2m">Hours → Minutes</option>
            <option value="m2d">Minutes → Days</option>
          </select>
        </label>
        <label className="flex flex-col text-xs gap-1">
          Value
          <input
            type="number"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm w-40"
            min={0}
          />
        </label>
        <div className="text-sm">
          <span className="text-zinc-500">= </span>
          <span className="font-mono">{out}</span>
        </div>
      </div>
    </section>
  );
}

export function ModifyPanel() {
  const { data: tasks, mutate } = useSWR<TaskRead[]>("/tasks", fetcher);
  const refresh = async () => {
    await mutate();
  };

  if (!tasks) return <div className="text-sm text-zinc-500">Loading…</div>;
  return (
    <div className="space-y-4">
      <EditSection
        heading="In House"
        processTypeFilter={(t) =>
          (t.process_type ?? "").toLowerCase() !== "outsource" && t.machine_number !== "OutSrc"
        }
        tasks={tasks}
        onSaved={refresh}
      />
      <EditSection
        heading="Out Source"
        processTypeFilter={(t) =>
          (t.process_type ?? "").toLowerCase() === "outsource" || t.machine_number === "OutSrc"
        }
        tasks={tasks}
        onSaved={refresh}
      />
      <TimeConverter />
    </div>
  );
}
