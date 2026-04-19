"use client";

import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import { Sparkline } from "@/components/charts/Sparkline";
import { cn } from "@/lib/utils";

export interface KpiCardProps {
  label: string;
  value: string;
  /** Optional secondary line beneath the headline value */
  hint?: string;
  /** Percent delta vs previous period; null hides the chip */
  delta?: number | null;
  /** Direction the delta is "good" — defaults to up */
  goodDirection?: "up" | "down";
  icon?: React.ReactNode;
  /** Sparkline values (ordered oldest → newest) */
  trend?: number[];
  trendColor?: string;
  loading?: boolean;
  className?: string;
  /** Animation stagger delay in ms */
  delay?: number;
  /** Render the sparkline as ascending bars instead of an area line */
  sparkVariant?: "area" | "bars";
}

export function KpiCard({
  label,
  value,
  hint,
  delta,
  goodDirection = "up",
  icon,
  trend,
  trendColor = "var(--primary)",
  loading,
  className,
  delay = 0,
  sparkVariant = "area",
}: KpiCardProps) {
  const positive = delta !== null && delta !== undefined && delta > 0;
  const negative = delta !== null && delta !== undefined && delta < 0;
  const flat = delta === 0;
  const isGood = positive
    ? goodDirection === "up"
    : negative
      ? goodDirection === "down"
      : null;

  return (
    <div
      className={cn(
        "ga-card reveal group relative overflow-hidden p-5",
        className
      )}
      style={{ ["--d" as string]: `${delay}ms` }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 text-[11.5px] font-semibold uppercase tracking-[0.12em] text-[color:var(--muted-foreground)]">
          {icon && (
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[color:var(--surface-2)] text-[color:var(--foreground)]">
              {icon}
            </span>
          )}
          {label}
        </div>
        {delta !== undefined && delta !== null && (
          <span
            className={cn(
              "chip",
              flat
                ? "bg-[color:var(--surface-2)] text-[color:var(--muted-foreground)]"
                : isGood
                  ? "bg-[#e6f4ea] text-[color:var(--success)]"
                  : "bg-[#fce8e6] text-[color:var(--danger)]"
            )}
          >
            {flat ? (
              <Minus className="h-3 w-3" />
            ) : positive ? (
              <ArrowUpRight className="h-3 w-3" />
            ) : (
              <ArrowDownRight className="h-3 w-3" />
            )}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>

      <div className="mt-4 flex items-end gap-2">
        {loading ? (
          <span className="skeleton h-9 w-32" />
        ) : (
          <span className="ticker text-[34px] leading-none text-[color:var(--foreground)]">
            {value}
          </span>
        )}
      </div>
      {hint && (
        <div className="mt-1.5 text-[11.5px] text-[color:var(--muted-foreground)]">
          {hint}
        </div>
      )}

      {trend && trend.length > 1 && (
        <div className="-mx-1 mt-4">
          <Sparkline
            data={trend}
            color={trendColor}
            variant={sparkVariant}
            height={42}
          />
        </div>
      )}

      {/* Decorative corner gradient */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background: `radial-gradient(closest-side, ${trendColor}22, transparent)`,
        }}
      />
    </div>
  );
}
