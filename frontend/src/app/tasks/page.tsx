"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import type { TaskRead } from "@/lib/types";

export default function TasksPage() {
  const { data, error, isLoading, mutate } = useSWR<TaskRead[]>("/tasks", fetcher);
  const [deleting, setDeleting] = useState<number | null>(null);

  async function handleDelete(id: number) {
    if (!confirm("Delete this task?")) return;
    setDeleting(id);
    try {
      await api.deleteTask(id);
      await mutate();
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Tasks</h1>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 text-red-800 p-3 text-sm">
          {String(error)}
        </div>
      )}

      {isLoading && <div className="text-sm text-zinc-500">Loading…</div>}

      {data && (
        <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase tracking-wide text-zinc-500 bg-zinc-50 dark:bg-zinc-900">
              <tr>
                <th className="text-left px-3 py-2">UID</th>
                <th className="text-left px-3 py-2">Product</th>
                <th className="text-left px-3 py-2">Comp</th>
                <th className="text-left px-3 py-2">Machine</th>
                <th className="text-right px-3 py-2">Qty</th>
                <th className="text-right px-3 py-2">Run/1k</th>
                <th className="text-left px-3 py-2">Order</th>
                <th className="text-left px-3 py-2">Promised</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.map((t) => (
                <tr key={t.id} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="px-3 py-2 font-mono">{t.unique_id}</td>
                  <td className="px-3 py-2">{t.product_name}</td>
                  <td className="px-3 py-2 font-mono">{t.component}</td>
                  <td className="px-3 py-2 font-mono">{t.machine_number}</td>
                  <td className="px-3 py-2 text-right">{t.quantity_required.toLocaleString()}</td>
                  <td className="px-3 py-2 text-right">{t.run_time_per_1000}</td>
                  <td className="px-3 py-2 text-xs">{t.order_processing_date.slice(0, 10)}</td>
                  <td className="px-3 py-2 text-xs">{t.promised_delivery_date.slice(0, 10)}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => handleDelete(t.id)}
                      disabled={deleting === t.id}
                      className="text-red-600 hover:underline text-xs disabled:opacity-50"
                    >
                      {deleting === t.id ? "…" : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-3 py-6 text-center text-zinc-500">
                    No tasks. Run{" "}
                    <code className="text-xs bg-zinc-100 dark:bg-zinc-800 px-1 rounded">
                      python -m scripts.import_excel
                    </code>{" "}
                    in the backend to load data.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
