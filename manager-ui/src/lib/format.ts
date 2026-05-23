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
