"use client";

import {
  Bar,
  CartesianGrid,
  Cell,
  BarChart as RechartsBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartTooltip, CHART_COLORS } from "./shared";

export interface BarChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  height?: number;
  color?: string;
  layout?: "horizontal" | "vertical";
  yTickFormatter?: (value: number) => string;
  xTickFormatter?: (value: string) => string;
  /** Use a different color per bar from the chart palette */
  rainbow?: boolean;
}

export function BarChart({
  data,
  xKey,
  yKey,
  height = 300,
  color = "var(--chart-1)",
  layout = "horizontal",
  yTickFormatter,
  xTickFormatter,
  rainbow = false,
}: BarChartProps) {
  const isVertical = layout === "vertical";
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart
          data={data}
          layout={layout}
          margin={{ top: 8, right: 16, left: 4, bottom: 4 }}
          barCategoryGap={isVertical ? 6 : "22%"}
        >
          <defs>
            <linearGradient id="bar-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.95} />
              <stop offset="100%" stopColor={color} stopOpacity={0.55} />
            </linearGradient>
            <linearGradient id="bar-grad-h" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={color} stopOpacity={0.55} />
              <stop offset="100%" stopColor={color} stopOpacity={0.95} />
            </linearGradient>
          </defs>
          <CartesianGrid
            stroke="var(--border)"
            strokeDasharray="2 4"
            vertical={isVertical}
            horizontal={!isVertical}
          />
          {isVertical ? (
            <>
              <XAxis
                type="number"
                stroke="var(--muted-foreground)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={yTickFormatter}
              />
              <YAxis
                type="category"
                dataKey={xKey}
                stroke="var(--muted-foreground)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                width={180}
                tickFormatter={xTickFormatter}
              />
            </>
          ) : (
            <>
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
            </>
          )}
          <Tooltip
            cursor={{ fill: "var(--muted)", opacity: 0.35 }}
            content={<ChartTooltip valueFormatter={yTickFormatter} />}
          />
          <Bar
            dataKey={yKey}
            radius={isVertical ? [0, 6, 6, 0] : [6, 6, 0, 0]}
            fill={isVertical ? "url(#bar-grad-h)" : "url(#bar-grad)"}
            isAnimationActive
            animationDuration={650}
          >
            {rainbow &&
              data.map((_, i) => (
                <Cell
                  key={i}
                  fill={CHART_COLORS[i % CHART_COLORS.length]}
                  fillOpacity={0.9}
                />
              ))}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
