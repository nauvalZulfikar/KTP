/**
 * Format a backend timestamp (UTC) in Asia/Jakarta (WIB, UTC+7).
 * If the ISO string lacks a timezone suffix we assume the backend sent UTC.
 * Returns "—" for null/undefined and passes through unparseable strings.
 */
const WIB_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Jakarta",
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

export function fmtJakarta(iso: string | null | undefined): string {
  if (!iso) return "—";
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(iso);
  const parseable = hasTz ? iso : iso + "Z";
  const d = new Date(parseable);
  if (Number.isNaN(d.getTime())) return iso;
  return `${WIB_FORMATTER.format(d)} WIB`;
}
