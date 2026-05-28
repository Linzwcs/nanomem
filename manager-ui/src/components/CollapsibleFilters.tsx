import { MouseEvent, ReactNode, useState } from "react";
import { ChevronRight, X } from "lucide-react";

export type ActiveFilter = {
  label: string;
  onClear: () => void;
};

type CollapsibleFiltersProps = {
  active: ActiveFilter[];
  children: ReactNode;
  emptyHint: string;
  onClearAll?: () => void;
};

export function CollapsibleFilters({
  active,
  children,
  emptyHint,
  onClearAll,
}: CollapsibleFiltersProps) {
  const [open, setOpen] = useState(active.length > 0);

  const handleChipClick = (event: MouseEvent, clear: () => void) => {
    event.preventDefault();
    event.stopPropagation();
    clear();
  };

  const handleClearAll = (event: MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    onClearAll?.();
  };

  return (
    <details
      className="filter-collapsible"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="filter-summary">
        <span className="filter-summary-head">
          <ChevronRight
            aria-hidden="true"
            className="filter-summary-caret"
            size={14}
          />
          <span className="filter-summary-label">
            Filters
            {active.length > 0 ? (
              <span className="filter-summary-count">{active.length}</span>
            ) : null}
          </span>
        </span>
        <span className="filter-summary-chips">
          {active.length === 0 ? (
            <span className="filter-hint">{emptyHint}</span>
          ) : (
            active.map((filter) => (
              <button
                aria-label={`Clear ${filter.label}`}
                className="filter-chip filter-chip-dismissable"
                key={filter.label}
                onClick={(event) => handleChipClick(event, filter.onClear)}
                type="button"
              >
                <span>{filter.label}</span>
                <X aria-hidden="true" size={11} />
              </button>
            ))
          )}
        </span>
        {active.length > 0 && onClearAll ? (
          <button
            className="ghost-button filter-summary-clear"
            onClick={handleClearAll}
            type="button"
          >
            Clear all
          </button>
        ) : null}
      </summary>
      <div className="filter-collapsible-body">{children}</div>
    </details>
  );
}
