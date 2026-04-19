import type { ScheduledAssignmentRead, TaskRead } from "./types";

export type DiffStatus = "same" | "moved" | "machine-changed" | "added" | "removed";

export type ScenarioSnapshot = {
  name: string;
  tasks: TaskRead[];
  assignments: ScheduledAssignmentRead[];
};

export type TaskDiff = {
  taskId: number;
  product: string;
  component: string;
  status: DiffStatus;
  aMachine?: string;
  bMachine?: string;
  aStartMs?: number;
  bStartMs?: number;
  aEndMs?: number;
  bEndMs?: number;
  startDeltaMs?: number;
  endDeltaMs?: number;
};

export type DiffResult = {
  diffs: TaskDiff[];
  statusByTaskIdA: Map<number, DiffStatus>;
  statusByTaskIdB: Map<number, DiffStatus>;
  summary: {
    total: number;
    same: number;
    moved: number;
    machineChanged: number;
    added: number;
    removed: number;
  };
};

const MOVE_THRESHOLD_MS = 60_000;

function collapseAssignments(
  assignments: ScheduledAssignmentRead[],
): Map<number, { start: number; end: number }> {
  const m = new Map<number, { start: number; end: number }>();
  for (const a of assignments) {
    const s = new Date(a.start_time).getTime();
    const e = new Date(a.end_time).getTime();
    const cur = m.get(a.task_id);
    if (!cur) m.set(a.task_id, { start: s, end: e });
    else m.set(a.task_id, { start: Math.min(cur.start, s), end: Math.max(cur.end, e) });
  }
  return m;
}

function indexTasks(tasks: TaskRead[]): Map<number, TaskRead> {
  const m = new Map<number, TaskRead>();
  for (const t of tasks) m.set(t.id, t);
  return m;
}

export function computeScenarioDiff(a: ScenarioSnapshot, b: ScenarioSnapshot): DiffResult {
  const aTasks = indexTasks(a.tasks);
  const bTasks = indexTasks(b.tasks);
  const aTimes = collapseAssignments(a.assignments);
  const bTimes = collapseAssignments(b.assignments);

  const allIds = new Set<number>([...aTasks.keys(), ...bTasks.keys()]);

  const diffs: TaskDiff[] = [];
  const statusByTaskIdA = new Map<number, DiffStatus>();
  const statusByTaskIdB = new Map<number, DiffStatus>();
  const summary = { total: 0, same: 0, moved: 0, machineChanged: 0, added: 0, removed: 0 };

  for (const id of allIds) {
    const ta = aTasks.get(id);
    const tb = bTasks.get(id);
    const sa = aTimes.get(id);
    const sb = bTimes.get(id);

    const product = tb?.product_name ?? ta?.product_name ?? "—";
    const component = tb?.component ?? ta?.component ?? "—";

    let status: DiffStatus;
    if (!ta || !sa) {
      status = "added";
    } else if (!tb || !sb) {
      status = "removed";
    } else if (ta.machine_number !== tb.machine_number) {
      status = "machine-changed";
    } else {
      const startDelta = Math.abs(sa.start - sb.start);
      const endDelta = Math.abs(sa.end - sb.end);
      status = startDelta > MOVE_THRESHOLD_MS || endDelta > MOVE_THRESHOLD_MS ? "moved" : "same";
    }

    diffs.push({
      taskId: id,
      product,
      component,
      status,
      aMachine: ta?.machine_number,
      bMachine: tb?.machine_number,
      aStartMs: sa?.start,
      bStartMs: sb?.start,
      aEndMs: sa?.end,
      bEndMs: sb?.end,
      startDeltaMs: sa && sb ? sb.start - sa.start : undefined,
      endDeltaMs: sa && sb ? sb.end - sa.end : undefined,
    });

    if (ta) statusByTaskIdA.set(id, status === "added" ? "added" : status);
    if (tb) statusByTaskIdB.set(id, status === "removed" ? "removed" : status);

    summary.total += 1;
    if (status === "same") summary.same += 1;
    else if (status === "moved") summary.moved += 1;
    else if (status === "machine-changed") summary.machineChanged += 1;
    else if (status === "added") summary.added += 1;
    else if (status === "removed") summary.removed += 1;
  }

  diffs.sort((x, y) => {
    const order: Record<DiffStatus, number> = {
      "machine-changed": 0,
      moved: 1,
      added: 2,
      removed: 3,
      same: 4,
    };
    const diff = order[x.status] - order[y.status];
    if (diff !== 0) return diff;
    return x.product.localeCompare(y.product) || x.taskId - y.taskId;
  });

  return { diffs, statusByTaskIdA, statusByTaskIdB, summary };
}

export function formatDurationDelta(ms: number): string {
  if (!Number.isFinite(ms)) return "—";
  const sign = ms >= 0 ? "+" : "−";
  const abs = Math.abs(ms);
  const hours = abs / 3_600_000;
  if (hours < 1) {
    const mins = Math.round(abs / 60_000);
    return `${sign}${mins}m`;
  }
  if (hours < 24) return `${sign}${hours.toFixed(1)}h`;
  return `${sign}${(hours / 24).toFixed(1)}d`;
}
