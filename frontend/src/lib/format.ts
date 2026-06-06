import type { BlockStatus } from "@/api/types";

export function minutesToLabel(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h && m) return `${h}h ${m}m`;
  if (h) return `${h}h`;
  return `${m}m`;
}

export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" });
}

export const STATUS_META: Record<BlockStatus, { label: string; cls: string }> = {
  planned: { label: "Planned", cls: "bg-white/10 text-muted" },
  completed: { label: "Did it", cls: "bg-good/20 text-good" },
  partial: { label: "Partial", cls: "bg-warn/20 text-warn" },
  missed: { label: "Missed", cls: "bg-bad/20 text-bad" },
  unlogged: { label: "Account for it", cls: "bg-brand/20 text-brand" },
};

const CATEGORY_COLORS: Record<string, string> = {
  Work: "#5b8cff",
  Study: "#7c5cff",
  Health: "#34d399",
  Social: "#f59e0b",
  Chores: "#22d3ee",
  Rest: "#a78bfa",
  "Social media": "#f87171",
};

export function categoryColor(category: string): string {
  return CATEGORY_COLORS[category] ?? "#8b93a7";
}
