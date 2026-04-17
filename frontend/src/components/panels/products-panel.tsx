"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { TaskCreate, TaskRead } from "@/lib/types";

function Banner({ kind, msg }: { kind: "ok" | "err"; msg: string }) {
  const c =
    kind === "ok"
      ? "border-emerald-300 bg-emerald-50 text-emerald-800"
      : "border-red-300 bg-red-50 text-red-800";
  return <div className={`rounded border ${c} px-3 py-2 text-xs`}>{msg}</div>;
}

function AddProduct({ tasks, onSaved }: { tasks: TaskRead[]; onSaved: () => Promise<void> }) {
  const products = useMemo(
    () => Array.from(new Set(tasks.map((t) => t.product_name))).sort(),
    [tasks]
  );
  const [productName, setProductName] = useState("");
  const existing = tasks.filter((t) => t.product_name === productName);
  const isExisting = existing.length > 0;

  const [orderDate, setOrderDate] = useState("");
  const [promisedDate, setPromisedDate] = useState("");
  const [quantity, setQuantity] = useState("1000");
  const [processType, setProcessType] = useState<"In House" | "Outsource">("In House");
  const [machineNumber, setMachineNumber] = useState("M1");
  const [runTime, setRunTime] = useState("30");
  const [cycleTime, setCycleTime] = useState("");
  const [setupTime, setSetupTime] = useState("");

  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const nextComponent = useMemo(() => {
    if (!isExisting) return "C1";
    const nums = existing
      .map((t) => parseInt(t.component.replace(/\D/g, ""), 10))
      .filter((n) => !Number.isNaN(n));
    return `C${Math.max(0, ...nums) + 1}`;
  }, [existing, isExisting]);

  const nextOperation = useMemo(() => {
    if (!isExisting) return "Op1";
    const nums = existing
      .map((t) => parseInt((t.operation ?? "").replace(/\D/g, ""), 10))
      .filter((n) => !Number.isNaN(n));
    return `Op${Math.max(0, ...nums) + 1}`;
  }, [existing, isExisting]);

  const nextUniqueId = useMemo(() => {
    const max = tasks.reduce((m, t) => Math.max(m, t.unique_id), 0);
    return max + 1;
  }, [tasks]);

  const inheritedOrder = isExisting ? existing[0].order_processing_date.slice(0, 10) : "";
  const inheritedPromised = isExisting ? existing[0].promised_delivery_date.slice(0, 10) : "";
  const inheritedQty = isExisting ? String(existing[0].quantity_required) : "";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    if (!productName.trim()) {
      setErr("Product name is required.");
      return;
    }
    const effectiveMachine = processType === "Outsource" ? "OutSrc" : machineNumber;
    const body: TaskCreate = {
      unique_id: nextUniqueId,
      product_name: productName,
      component: nextComponent,
      operation: nextOperation,
      process_type: processType,
      machine_number: effectiveMachine,
      order_processing_date: new Date(isExisting ? inheritedOrder : orderDate).toISOString(),
      promised_delivery_date: new Date(isExisting ? inheritedPromised : promisedDate).toISOString(),
      quantity_required: Number(isExisting ? inheritedQty : quantity),
      run_time_per_1000: Number(runTime),
      cycle_time_seconds: cycleTime ? Number(cycleTime) : null,
      setup_time_seconds: setupTime ? Number(setupTime) : null,
      status: "InProgress",
    };
    try {
      setSaving(true);
      await api.createTask(body);
      await onSaved();
      setMsg(`Added ${productName} / ${nextComponent} (${nextOperation}).`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3">
      <h2 className="text-base font-medium">Add Products</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="flex flex-col text-xs gap-1 md:col-span-2">
          Product name (existing products extend with the next component)
          <input
            list="products-list"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
            placeholder="Product 8"
            required
          />
          <datalist id="products-list">
            {products.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
        </label>
        <div className="flex flex-col text-xs gap-1">
          <span>Next IDs</span>
          <div className="text-sm font-mono text-zinc-700 dark:text-zinc-300">
            UID {nextUniqueId} · {nextComponent} · {nextOperation}
          </div>
        </div>

        <label className="flex flex-col text-xs gap-1">
          Order date {isExisting && <span className="text-zinc-500">(inherited)</span>}
          <input
            type="date"
            value={isExisting ? inheritedOrder : orderDate}
            onChange={(e) => setOrderDate(e.target.value)}
            disabled={isExisting}
            required={!isExisting}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm disabled:opacity-60"
          />
        </label>
        <label className="flex flex-col text-xs gap-1">
          Promised date {isExisting && <span className="text-zinc-500">(inherited)</span>}
          <input
            type="date"
            value={isExisting ? inheritedPromised : promisedDate}
            onChange={(e) => setPromisedDate(e.target.value)}
            disabled={isExisting}
            required={!isExisting}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm disabled:opacity-60"
          />
        </label>
        <label className="flex flex-col text-xs gap-1">
          Quantity required {isExisting && <span className="text-zinc-500">(inherited)</span>}
          <input
            type="number"
            value={isExisting ? inheritedQty : quantity}
            onChange={(e) => setQuantity(e.target.value)}
            disabled={isExisting}
            required
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm disabled:opacity-60"
          />
        </label>

        <label className="flex flex-col text-xs gap-1">
          Process type
          <select
            value={processType}
            onChange={(e) => setProcessType(e.target.value as "In House" | "Outsource")}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          >
            <option value="In House">In House</option>
            <option value="Outsource">Outsource</option>
          </select>
        </label>
        <label className="flex flex-col text-xs gap-1">
          Machine number
          <input
            value={processType === "Outsource" ? "OutSrc" : machineNumber}
            onChange={(e) => setMachineNumber(e.target.value)}
            disabled={processType === "Outsource"}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm disabled:opacity-60"
          />
        </label>
        <label className="flex flex-col text-xs gap-1">
          Run time (min/1000)
          <input
            type="number"
            value={runTime}
            onChange={(e) => setRunTime(e.target.value)}
            required
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col text-xs gap-1">
          Cycle time (sec)
          <input
            type="number"
            step="0.01"
            value={cycleTime}
            onChange={(e) => setCycleTime(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          />
        </label>
        <label className="flex flex-col text-xs gap-1">
          Setup time (sec)
          <input
            type="number"
            value={setupTime}
            onChange={(e) => setSetupTime(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          />
        </label>

        <div className="md:col-span-3 flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-1.5 rounded-md bg-sky-600 text-white text-xs font-medium disabled:opacity-50 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-400 shadow-sm"
          >
            {saving ? "Saving…" : "Submit"}
          </button>
          {msg && <Banner kind="ok" msg={msg} />}
          {err && <Banner kind="err" msg={err} />}
        </div>
      </form>
    </section>
  );
}

function DeleteProduct({ tasks, onSaved }: { tasks: TaskRead[]; onSaved: () => Promise<void> }) {
  const products = useMemo(
    () => Array.from(new Set(tasks.map((t) => t.product_name))).sort(),
    [tasks]
  );
  const [product, setProduct] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleDelete() {
    if (!product) return;
    const rows = tasks.filter((t) => t.product_name === product);
    if (!confirm(`Delete ${rows.length} rows for ${product}?`)) return;
    setMsg(null);
    setErr(null);
    setBusy(true);
    try {
      for (const r of rows) {
        await api.deleteTask(r.id);
      }
      await onSaved();
      setMsg(`Deleted ${rows.length} rows for ${product}.`);
      setProduct("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3">
      <h2 className="text-base font-medium">Delete Products</h2>
      <div className="flex items-end gap-3 flex-wrap">
        <label className="flex flex-col text-xs gap-1">
          Product
          <select
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm min-w-[200px]"
          >
            <option value="">—</option>
            {products.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={handleDelete}
          disabled={!product || busy}
          className="px-4 py-1.5 rounded-md bg-red-600 text-white text-xs font-medium disabled:opacity-50 hover:bg-red-700"
        >
          {busy ? "Deleting…" : "Delete"}
        </button>
        {msg && <Banner kind="ok" msg={msg} />}
        {err && <Banner kind="err" msg={err} />}
      </div>
    </section>
  );
}

function ChangeDueDate({ tasks, onSaved }: { tasks: TaskRead[]; onSaved: () => Promise<void> }) {
  const products = useMemo(
    () => Array.from(new Set(tasks.map((t) => t.product_name))).sort(),
    [tasks]
  );
  const [product, setProduct] = useState("");
  const [date, setDate] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleConfirm() {
    if (!product || !date) return;
    const rows = tasks.filter((t) => t.product_name === product);
    setMsg(null);
    setErr(null);
    setBusy(true);
    try {
      const iso = new Date(date).toISOString();
      for (const r of rows) {
        await api.updateTask(r.id, { promised_delivery_date: iso });
      }
      await onSaved();
      setMsg(`Updated promised date to ${date} for ${product} (${rows.length} rows).`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 space-y-3">
      <h2 className="text-base font-medium">Change Due Date</h2>
      <div className="flex items-end gap-3 flex-wrap">
        <label className="flex flex-col text-xs gap-1">
          Product
          <select
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm min-w-[200px]"
          >
            <option value="">—</option>
            {products.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs gap-1">
          New promised delivery date
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 px-2 py-1.5 text-sm"
          />
        </label>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={!product || !date || busy}
          className="px-4 py-1.5 rounded-md bg-sky-600 text-white text-xs font-medium disabled:opacity-50 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-400 shadow-sm"
        >
          {busy ? "Saving…" : "Confirm"}
        </button>
        {msg && <Banner kind="ok" msg={msg} />}
        {err && <Banner kind="err" msg={err} />}
      </div>
    </section>
  );
}

export function ProductsPanel() {
  const { data: tasks, mutate } = useSWR<TaskRead[]>("/tasks", fetcher);
  const refresh = async () => {
    await mutate();
  };

  if (!tasks) return <div className="text-sm text-zinc-500">Loading…</div>;
  return (
    <div className="space-y-4">
      <AddProduct tasks={tasks} onSaved={refresh} />
      <DeleteProduct tasks={tasks} onSaved={refresh} />
      <ChangeDueDate tasks={tasks} onSaved={refresh} />
    </div>
  );
}
