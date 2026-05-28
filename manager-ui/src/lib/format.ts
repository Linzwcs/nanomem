export function formatTime(value: string | null | undefined) {
  if (!value) return "none";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    hour12: false,
    timeStyle: "short",
  }).format(date);
}

/**
 * Single-line compact timestamp for dense audit tables, e.g. "5/27/26 17:36".
 * Drops the verbose "May 27, 2026, 17:36" wrap to two lines.
 */
export function formatTimeShort(value: string | null | undefined) {
  if (!value) return "none";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const dateText = new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(date);
  const timeText = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
  return `${dateText} ${timeText}`;
}

export function formatNumber(value: unknown) {
  return typeof value === "number" ? value.toLocaleString("en-US") : String(value ?? "0");
}

export function jsonPreview(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

/**
 * Visually shorten a long opaque id while keeping head + tail recognizable.
 * Example: truncateId("dlg_ff7a7dae8d6146d696698294") → "dlg_ff7a…698294"
 */
export function truncateId(value: string, head = 9, tail = 6) {
  if (!value) return "";
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

