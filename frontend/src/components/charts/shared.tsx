"use client";

import type { TooltipContentProps } from "recharts";

export const CHART_COLORS = [
  "#1a73e8", // primary blue
  "#0b8d77", // teal accent
  "#f29900", // amber
  "#d93025", // red
  "#ab47bc", // purple
  "#00acc1", // cyan
  "#ff7043", // orange
  "#5e7ce0", // periwinkle
];

type Item = {
  name?: string | number;
  value?: number | string;
  color?: string;
  dataKey?: string | number;
};

export function ChartTooltip({
  active,
  payload,
  label,
  valueFormatter,
}: Partial<TooltipContentProps<number, string>> & {
  valueFormatter?: (v: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const items = payload as unknown as Item[];

  return (
    <div className="ga-card overflow-hidden border border-[color:var(--border-strong)] !rounded-lg bg-[color:var(--surface)] px-3 py-2 text-[12px] shadow-xl">
      {label !== undefined && label !== "" && (
        <div className="mb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-[color:var(--muted-foreground)]">
          {String(label)}
        </div>
      )}
      <ul className="space-y-1">
        {items.map((it, i) => {
          const num = typeof it.value === "number" ? it.value : Number(it.value);
          return (
            <li
              key={i}
              className="flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-2">
                <span
                  className="h-2 w-2 rounded-sm"
                  style={{ backgroundColor: it.color }}
                />
                <span className="text-[color:var(--muted-foreground)]">
                  {String(it.name ?? it.dataKey ?? "")}
                </span>
              </div>
              <span className="font-num text-[color:var(--foreground)]">
                {Number.isFinite(num)
                  ? valueFormatter
                    ? valueFormatter(num)
                    : num.toLocaleString("ja-JP")
                  : String(it.value)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
