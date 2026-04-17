"use client";

import { useState } from "react";
import { exportToExcel } from "@/lib/excel-export";

export function ExportButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handle() {
    setError(null);
    setBusy(true);
    try {
      await exportToExcel();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handle}
        disabled={busy}
        className="px-3 py-2 rounded-md text-sm border border-emerald-300 text-emerald-800 bg-emerald-50 hover:bg-emerald-100 disabled:opacity-50 shadow-sm"
        title="Export No MSJS + latest run + catalogue tables (with charts) to an .xlsx file"
      >
        {busy ? "Exporting…" : "Export .xlsx"}
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
