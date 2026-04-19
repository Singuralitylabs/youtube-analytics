"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartTooltip, CHART_COLORS } from "./shared";

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
  /** Render a soft gradient under the first series (best for single-series charts) */
  area?: boolean;
}

export function LineChart({
  data,
  xKey,
  series,
  height = 300,
  yTickFormatter,
  xTickFormatter,
  area = true,
}: LineChartProps) {
  const showArea = area && series.length === 1;

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={data}
          margin={{ top: 12, right: 16, left: 4, bottom: 6 }}
        >
          <defs>
            {series.map((s, i) => {
              const color = s.color ?? CHART_COLORS[i % CHART_COLORS.length];
              return (
                <linearGradient
                  key={s.key}
                  id={`grad-${s.key}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              );
            })}
          </defs>
          <CartesianGrid
            stroke="var(--border)"
            strokeDasharray="2 4"
            vertical={false}
          />
          <XAxis
            dataKey={xKey}
            stroke="var(--muted-foreground)"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
            tickFormatter={xTickFormatter}
            dy={4}
          />
          <YAxis
            stroke="var(--muted-foreground)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={yTickFormatter}
            width={56}
          />
          <Tooltip
            cursor={{
              stroke: "var(--border-strong)",
              strokeDasharray: "3 3",
            }}
            content={
              <ChartTooltip
                valueFormatter={yTickFormatter}
              />
            }
          />
          {series.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
              iconType="circle"
              iconSize={8}
            />
          )}
          {showArea &&
            series.map((s, i) => {
              const color = s.color ?? CHART_COLORS[i % CHART_COLORS.length];
              return (
                <Area
                  key={`area-${s.key}`}
                  type="monotone"
                  dataKey={s.key}
                  stroke="none"
                  fill={`url(#grad-${s.key})`}
                  isAnimationActive
                  animationDuration={700}
                />
              );
            })}
          {series.map((s, i) => {
            const color = s.color ?? CHART_COLORS[i % CHART_COLORS.length];
            return (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name ?? s.key}
                stroke={color}
                strokeWidth={2.25}
                dot={false}
                activeDot={{
                  r: 4,
                  strokeWidth: 2,
                  stroke: "var(--surface)",
                  fill: color,
                }}
                isAnimationActive
                animationDuration={700}
              />
            );
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
