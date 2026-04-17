"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { api, fetcher } from "@/lib/api";
import { fmtJakarta } from "@/lib/datetime";
import type { ScheduleRunRead } from "@/lib/types";

export default function RunsPage() {
  const { data, error, isLoading, mutate } = useSWR<ScheduleRunRead[]>("/runs", fetcher);
  const [busy, setBusy] = useState(false);
  const [resetErr, setResetErr] = useState<string | null>(null);
  const [resetMsg, setResetMsg] = useState<string | null>(null);

  async function handleReset() {
    if (!confirm(`Delete all ${data?.length ?? 0} runs? IDs restart from #1. Master tasks are NOT touched.`)) {
      return;
    }
    setBusy(true);
    setResetErr(null);
    setResetMsg(null);
    try {
      await api.deleteAllRuns();
      await mutate();
      setResetMsg("All runs cleared. Next scheduler run will be #1.");
    } catch (e) {
      setResetErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-2xl font-semibold">Schedule runs</h1>
        <button
          type="button"
          onClick={handleReset}
          disabled={busy || !data || data.length === 0}
          className="px-3 py-1.5 rounded-md text-xs border border-red-300 text-red-700 bg-red-50 hover:bg-red-100 disabled:opacity-50 shadow-sm"
          title="Delete every schedule run; next run will be #1"
        >
          {busy ? "Resetting…" : "Reset runs"}
        </button>
      </div>

      {resetMsg && (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 text-emerald-800 px-3 py-2 text-sm">
          {resetMsg}
        </div>
      )}
      {resetErr && (
        <div className="rounded-md border border-red-300 bg-red-50 text-red-800 px-3 py-2 text-sm">
          {resetErr}
        </div>
      )}
      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 text-red-800 p-3 text-sm">
          {String(error)}
        </div>
      )}
      {isLoading && <div className="text-sm text-zinc-500">Loading…</div>}

      {data && data.length === 0 && (
        <div className="text-sm text-zinc-500">No runs yet.</div>
      )}

      {data && data.length > 0 && (
        <ul className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 divide-y divide-zinc-100 dark:divide-zinc-800">
          {data.map((r) => (
            <li key={r.id}>
              <Link
                href={`/runs/${r.id}`}
                className="flex justify-between items-center px-4 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-900"
              >
                <div>
                  <div className="font-medium">Run #{r.id}</div>
                  <div className="text-xs text-zinc-500">{fmtJakarta(r.created_at)}</div>
                </div>
                {r.notes && <div className="text-xs text-zinc-500 max-w-xs truncate">{r.notes}</div>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
