import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number | undefined | null): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "-";
  return n.toLocaleString("ja-JP");
}

export function formatDuration(sec: number | undefined | null): string {
  if (sec === undefined || sec === null || Number.isNaN(sec)) return "-";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function formatDate(d: string | undefined | null): string {
  if (!d) return "-";
  return d.split("T")[0] ?? d;
}

/** Compact number formatter: 1234 → 1.2K, 1500000 → 1.5M */
export function formatCompact(n: number | undefined | null): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "-";
  const abs = Math.abs(n);
  if (abs >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

/** Percent delta between current and previous values; null if previous is 0/undefined */
export function pctDelta(
  current: number | undefined | null,
  previous: number | undefined | null
): number | null {
  if (
    current === undefined ||
    current === null ||
    previous === undefined ||
    previous === null ||
    previous === 0
  ) {
    return null;
  }
  return ((current - previous) / previous) * 100;
}

/** Short MM/DD form for chart axes when keys look like YYYY-MM-DD */
export function formatShortDate(s: string | undefined | null): string {
  if (!s) return "-";
  const d = s.split("T")[0] ?? s;
  const parts = d.split("-");
  if (parts.length === 3) return `${parts[1]}/${parts[2]}`;
  return d;
}
