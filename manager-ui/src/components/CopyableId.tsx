import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { truncateId } from "../lib/format";

type CopyableIdProps = {
  value: string;
  /** When provided, override the truncated display text (e.g. with a fuller prefix). */
  display?: string;
  /** Wrap the id chip in this tag (default "span"). */
  as?: "span" | "strong";
  /** Visual variant. */
  variant?: "default" | "compact";
};

/**
 * Truncated, monospace id with a copy-to-clipboard affordance.
 *
 * Click anywhere on the chip to copy the full value. A check icon
 * briefly replaces the copy icon to confirm. The full id is also
 * available on the underlying button's `title` attribute (tooltip on
 * hover).
 */
export function CopyableId({
  value,
  display,
  as = "span",
  variant = "default",
}: CopyableIdProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1100);
    } catch {
      // clipboard may be unavailable in non-secure contexts; silently skip
    }
  };

  const Wrapper = as;
  const Icon = copied ? Check : Copy;
  const label = display ?? truncateId(value);

  return (
    <Wrapper className={`copyable-id copyable-id-${variant}`}>
      <button
        aria-label={copied ? "Copied" : `Copy ${value}`}
        className="copyable-id-button"
        onClick={handleCopy}
        title={value}
        type="button"
      >
        <span className="copyable-id-text">{label}</span>
        <Icon
          aria-hidden
          className={`copyable-id-icon${copied ? " copyable-id-icon-copied" : ""}`}
          size={variant === "compact" ? 12 : 13}
        />
      </button>
    </Wrapper>
  );
}
