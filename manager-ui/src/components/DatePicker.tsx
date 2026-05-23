import { useEffect, useId, useMemo, useRef, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";

type DatePickerProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
};

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function DatePicker({ label, value, onChange }: DatePickerProps) {
  const id = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const selectedDate = useMemo(() => parseDateValue(value), [value]);
  const [open, setOpen] = useState(false);
  const [viewDate, setViewDate] = useState(() =>
    startOfMonth(selectedDate ?? new Date()),
  );

  useEffect(() => {
    if (open) setViewDate(startOfMonth(selectedDate ?? new Date()));
  }, [open, selectedDate]);

  useEffect(() => {
    if (!open) return;
    function closeOnOutsideClick(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, [open]);

  const days = useMemo(() => monthGridDays(viewDate), [viewDate]);
  const todayValue = dateInputValue(new Date());

  function selectDate(day: number) {
    onChange(dateInputValue(new Date(viewDate.getFullYear(), viewDate.getMonth(), day)));
    setOpen(false);
  }

  return (
    <div className="date-picker-field" ref={rootRef}>
      <label className="date-picker-label" htmlFor={id}>
        {label}
      </label>
      <div className="date-picker-control">
        <input
          id={id}
          inputMode="numeric"
          maxLength={10}
          onChange={(event) => updateTextValue(event.target.value, onChange)}
          onFocus={() => setOpen(true)}
          pattern="\\d{4}-\\d{2}-\\d{2}"
          placeholder="YYYY-MM-DD"
          title="YYYY-MM-DD"
          type="text"
          value={value}
        />
        <button
          aria-expanded={open}
          aria-label={`Open ${label} calendar`}
          className="icon-button date-picker-trigger"
          onClick={() => setOpen((current) => !current)}
          type="button"
        >
          <CalendarDays aria-hidden="true" size={15} />
        </button>
      </div>
      {open && (
        <div className="date-picker-popover" role="dialog" aria-label={`${label} calendar`}>
          <div className="date-picker-header">
            <button
              aria-label="Previous month"
              className="icon-button"
              onClick={() => setViewDate(addMonths(viewDate, -1))}
              type="button"
            >
              <ChevronLeft aria-hidden="true" size={15} />
            </button>
            <strong>
              {MONTHS[viewDate.getMonth()]} {viewDate.getFullYear()}
            </strong>
            <button
              aria-label="Next month"
              className="icon-button"
              onClick={() => setViewDate(addMonths(viewDate, 1))}
              type="button"
            >
              <ChevronRight aria-hidden="true" size={15} />
            </button>
          </div>
          <div className="date-picker-weekdays">
            {WEEKDAYS.map((day) => (
              <span key={day}>{day}</span>
            ))}
          </div>
          <div className="date-picker-grid">
            {days.map((day, index) =>
              day === null ? (
                <span aria-hidden="true" key={`blank-${index}`} />
              ) : (
                <button
                  className={dateButtonClass(
                    dateInputValue(
                      new Date(viewDate.getFullYear(), viewDate.getMonth(), day),
                    ),
                    value,
                    todayValue,
                  )}
                  key={day}
                  onClick={() => selectDate(day)}
                  type="button"
                >
                  {day}
                </button>
              ),
            )}
          </div>
          <div className="date-picker-footer">
            <button className="ghost-button" onClick={() => onChange("")} type="button">
              Clear
            </button>
            <button
              className="ghost-button"
              onClick={() => {
                onChange(todayValue);
                setViewDate(startOfMonth(new Date()));
                setOpen(false);
              }}
              type="button"
            >
              Today
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function updateTextValue(value: string, onChange: (value: string) => void) {
  if (/^[0-9-]*$/.test(value) && value.length <= 10) onChange(value);
}

function parseDateValue(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return Number.isNaN(date.getTime()) ? null : date;
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addMonths(date: Date, offset: number) {
  return new Date(date.getFullYear(), date.getMonth() + offset, 1);
}

function monthGridDays(date: Date) {
  const firstDay = new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  const count = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  return [
    ...Array.from({ length: firstDay }, () => null),
    ...Array.from({ length: count }, (_, index) => index + 1),
  ];
}

function dateInputValue(date: Date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10);
}

function dateButtonClass(dayValue: string, selectedValue: string, todayValue: string) {
  return [
    "date-picker-day",
    dayValue === selectedValue ? "date-picker-day-selected" : "",
    dayValue === todayValue ? "date-picker-day-today" : "",
  ]
    .filter(Boolean)
    .join(" ");
}
