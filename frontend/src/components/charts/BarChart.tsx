"use client";

import {
  Bar,
  CartesianGrid,
  BarChart as RechartsBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface BarChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  height?: number;
  color?: string;
  layout?: "horizontal" | "vertical";
  yTickFormatter?: (value: number) => string;
  xTickFormatter?: (value: string) => string;
}

export function BarChart({
  data,
  xKey,
  yKey,
  height = 300,
  color = "#2563eb",
  layout = "horizontal",
  yTickFormatter,
  xTickFormatter,
}: BarChartProps) {
  const isVertical = layout === "vertical";
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart
          data={data}
          layout={layout}
          margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          {isVertical ? (
            <>
              <XAxis
                type="number"
                stroke="var(--muted-foreground)"
                fontSize={12}
                tickFormatter={yTickFormatter}
              />
              <YAxis
                type="category"
                dataKey={xKey}
                stroke="var(--muted-foreground)"
                fontSize={12}
                width={160}
                tickFormatter={xTickFormatter}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey={xKey}
                stroke="var(--muted-foreground)"
                fontSize={12}
                tickFormatter={xTickFormatter}
              />
              <YAxis
                stroke="var(--muted-foreground)"
                fontSize={12}
                tickFormatter={yTickFormatter}
              />
            </>
          )}
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          />
          <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
