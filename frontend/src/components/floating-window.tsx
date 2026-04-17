"use client";

import { useEffect } from "react";

type Props = {
  title: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  width?: number;
};

export function FloatingWindow({ title, open, onClose, children, width = 880 }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 backdrop-blur-sm p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="relative bg-white dark:bg-zinc-950 rounded-lg border border-sky-100 dark:border-zinc-800 shadow-2xl flex flex-col max-h-[85vh] w-full"
        style={{ maxWidth: width }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={title}
        aria-modal="true"
      >
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-sky-100 dark:border-zinc-800 bg-sky-50 dark:bg-zinc-900 rounded-t-lg">
          <div className="font-medium text-sm text-sky-900 dark:text-zinc-100">{title}</div>
          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded hover:bg-sky-100 dark:hover:bg-zinc-800 text-sky-700 dark:text-zinc-400 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4">{children}</div>
      </div>
    </div>
  );
}
