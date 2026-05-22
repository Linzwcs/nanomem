import type { ReactNode } from "react";

type BadgeProps = {
  tone?: "neutral" | "good" | "warn" | "muted";
  children: ReactNode;
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{children ?? "none"}</span>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className="empty-state">{message}</div>;
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);
  return <div className="error-state">{message}</div>;
}

export function LoadingState() {
  return <div className="loading-state">Loading...</div>;
}
