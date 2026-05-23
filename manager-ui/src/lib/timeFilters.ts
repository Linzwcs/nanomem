const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export type DateRangeValue = {
  start: string;
  end: string;
};

export function apiTimeRange(value: DateRangeValue) {
  return {
    start: dateBoundaryToIso(value.start, "start"),
    end: dateBoundaryToIso(value.end, "end"),
  };
}

export function timeRangePayload(value: DateRangeValue) {
  const range = apiTimeRange(value);
  return range.start || range.end ? range : null;
}

export function localDateTimeToIso(value: string) {
  if (!value) return new Date().toISOString();
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
}

export function nowDateTimeInputValue() {
  const date = new Date();
  date.setSeconds(0, 0);
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

export function presetDateRange(preset: string): DateRangeValue {
  if (preset === "all") return { start: "", end: "" };
  if (preset === "month") {
    const now = new Date();
    return {
      start: dateInputValue(new Date(now.getFullYear(), now.getMonth(), 1)),
      end: dateInputValue(now),
    };
  }
  const days = Number(preset);
  if (Number.isFinite(days) && days > 0) {
    const now = new Date();
    const start = new Date(now);
    start.setDate(now.getDate() - days + 1);
    return { start: dateInputValue(start), end: dateInputValue(now) };
  }
  return { start: "", end: "" };
}

export function effectiveTimeRangeLabel(value: DateRangeValue) {
  const range = apiTimeRange(value);
  if (!range.start && !range.end) return "All time";
  return `From ${range.start ?? "the beginning"} to ${range.end ?? "now"}`;
}

function dateBoundaryToIso(value: string, boundary: "start" | "end") {
  const text = value.trim();
  if (!text) return undefined;
  if (!DATE_PATTERN.test(text)) return text;
  const [year, month, day] = text.split("-").map(Number);
  const date =
    boundary === "start"
      ? new Date(year, month - 1, day, 0, 0, 0, 0)
      : new Date(year, month - 1, day, 23, 59, 59, 999);
  return date.toISOString();
}

function dateInputValue(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10);
}
