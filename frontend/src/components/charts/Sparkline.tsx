"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
} from "recharts";

export interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
  /** Render as bars instead of an area line */
  variant?: "area" | "bars";
}

export function Sparkline({
  data,
  color = "var(--primary)",
  height = 44,
  variant = "area",
}: SparklineProps) {
  // Synthesize a stable shape if no data provided so layouts don't collapse.
  const points = (data && data.length > 0 ? data : [0, 0, 0, 0]).map(
    (v, i) => ({ i, v })
  );

  if (variant === "bars") {
    const max = Math.max(...points.map((p) => p.v), 1);
    return (
      <div
        className="flex h-full w-full items-end gap-[2px]"
        style={{ height }}
      >
        {points.map((p) => (
          <span
            key={p.i}
            style={{
              height: `${Math.max((p.v / max) * 100, 6)}%`,
              background: color,
              opacity: 0.45 + 0.55 * (p.v / max),
            }}
            className="flex-1 rounded-sm"
          />
        ))}
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={points}
          margin={{ top: 2, right: 0, bottom: 0, left: 0 }}
        >
          <defs>
            <linearGradient id={`spark-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.75}
            fill={`url(#spark-${color})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
