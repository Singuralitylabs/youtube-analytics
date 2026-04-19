"use client";

import {
  Cell,
  Pie,
  PieChart as RechartsPieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { ChartTooltip, CHART_COLORS } from "./shared";

export interface PieChartProps {
  data: { name: string; value: number }[];
  height?: number;
  colors?: string[];
}

export function PieChart({
  data,
  height = 300,
  colors = CHART_COLORS,
}: PieChartProps) {
  const total = data.reduce((sum, d) => sum + (d.value || 0), 0) || 1;

  return (
    <div className="flex h-full w-full flex-col gap-4 lg:flex-row lg:items-center">
      <div className="flex-1" style={{ minHeight: height, height }}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsPieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius="58%"
              outerRadius="86%"
              paddingAngle={1.2}
              stroke="var(--surface)"
              strokeWidth={2}
              isAnimationActive
              animationDuration={700}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip
              content={
                <ChartTooltip
                  valueFormatter={(v) =>
                    `${v.toLocaleString("ja-JP")} (${((v / total) * 100).toFixed(1)}%)`
                  }
                />
              }
            />
          </RechartsPieChart>
        </ResponsiveContainer>
      </div>
      <ul className="grid w-full shrink-0 grid-cols-1 gap-1.5 text-[12px] lg:max-w-[260px]">
        {data.map((d, i) => {
          const pct = (d.value / total) * 100;
          return (
            <li
              key={d.name + i}
              className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 hover:bg-[color:var(--surface-2)]"
            >
              <div className="flex min-w-0 items-center gap-2">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ background: colors[i % colors.length] }}
                />
                <span className="truncate text-[color:var(--foreground)]">
                  {d.name}
                </span>
              </div>
              <span className="font-num shrink-0 text-[color:var(--muted-foreground)]">
                {pct.toFixed(1)}%
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
