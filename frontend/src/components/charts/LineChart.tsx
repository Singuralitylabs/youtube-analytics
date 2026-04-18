"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface LineSeries {
  key: string;
  name?: string;
  color?: string;
}

export interface LineChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  series: LineSeries[];
  height?: number;
  yTickFormatter?: (value: number) => string;
  xTickFormatter?: (value: string) => string;
}

const DEFAULT_COLORS = [
  "#2563eb",
  "#dc2626",
  "#16a34a",
  "#ca8a04",
  "#9333ea",
  "#0891b2",
  "#db2777",
  "#ea580c",
];

export function LineChart({
  data,
  xKey,
  series,
  height = 300,
  yTickFormatter,
  xTickFormatter,
}: LineChartProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart
          data={data}
          margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
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
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: "12px" }} />}
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name ?? s.key}
              stroke={s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </div>
  );
}
