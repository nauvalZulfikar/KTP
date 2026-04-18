import Link from "next/link";

export function Nav() {
  return (
    <nav className="border-b border-sky-100 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950 backdrop-blur-sm sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="font-semibold text-sky-700 dark:text-sky-400">Machine Scheduler</Link>
        <div className="flex gap-4 text-sm text-zinc-600 dark:text-zinc-400">
          <Link href="/" className="hover:text-zinc-900 dark:hover:text-zinc-100">Dashboard</Link>
          <Link href="/tasks" className="hover:text-zinc-900 dark:hover:text-zinc-100">Tasks</Link>
          <Link href="/catalogue" className="hover:text-zinc-900 dark:hover:text-zinc-100">Catalogue</Link>
        </div>
      </div>
    </nav>
  );
}
