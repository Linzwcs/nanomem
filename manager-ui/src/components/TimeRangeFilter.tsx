import { CalendarDays } from "lucide-react";

import { DatePicker } from "./DatePicker";
import {
  effectiveTimeRangeLabel,
  presetDateRange,
  type DateRangeValue,
} from "../lib/timeFilters";

type TimeRangeFilterProps = {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
  compact?: boolean;
};

const presets = [
  { label: "All", value: "all" },
  { label: "Last 7 days", value: "7" },
  { label: "Last 30 days", value: "30" },
  { label: "Last 90 days", value: "90" },
  { label: "This month", value: "month" },
];

export function TimeRangeFilter({
  value,
  onChange,
  compact = false,
}: TimeRangeFilterProps) {
  const activePreset = currentPreset(value);

  return (
    <div className={`time-filter${compact ? " time-filter-compact" : ""}`}>
      <div className="time-filter-presets" aria-label="Time range presets">
        {presets.map((preset) => (
          <button
            aria-pressed={activePreset === preset.value}
            className={`ghost-button preset-button${
              activePreset === preset.value ? " preset-button-active" : ""
            }`}
            key={preset.value}
            onClick={() => onChange(presetDateRange(preset.value))}
            type="button"
          >
            {preset.label}
          </button>
        ))}
      </div>
      <div className="time-filter-fields">
        <DatePicker
          label="Start date"
          value={value.start}
          onChange={(start) => onChange({ ...value, start })}
        />
        <DatePicker
          label="End date"
          value={value.end}
          onChange={(end) => onChange({ ...value, end })}
        />
      </div>
      <div className="time-filter-effective">
        <CalendarDays aria-hidden="true" size={15} />
        <span>{effectiveTimeRangeLabel(value)}</span>
      </div>
    </div>
  );
}

function currentPreset(value: DateRangeValue) {
  return presets.find((preset) => sameRange(value, presetDateRange(preset.value)))
    ?.value;
}

function sameRange(left: DateRangeValue, right: DateRangeValue) {
  return left.start === right.start && left.end === right.end;
}
