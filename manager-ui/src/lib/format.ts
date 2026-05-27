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

