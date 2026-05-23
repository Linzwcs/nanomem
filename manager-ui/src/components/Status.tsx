import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";

type BadgeProps = {
  tone?: "neutral" | "good" | "warn" | "muted";
  children: ReactNode;
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{children ?? "none"}</span>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className="status-state empty-state">{message}</div>;
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);
  return <div className="status-state error-state">{message}</div>;
}

export function LoadingState() {
  return (
    <div className="status-state loading-state">
      <Loader2 aria-hidden="true" className="loading-spinner" size={16} />
      <span>Loading</span>
    </div>
  );
}
