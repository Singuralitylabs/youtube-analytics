"use client";

import { cn } from "@/lib/utils";

export interface SegmentedOption<V extends string> {
  value: V;
  label: string;
}

export interface SegmentedControlProps<V extends string> {
  value: V;
  onChange: (v: V) => void;
  options: SegmentedOption<V>[];
  size?: "sm" | "md";
  className?: string;
  /** Aria label for the control */
  label?: string;
}

export function SegmentedControl<V extends string>({
  value,
  onChange,
  options,
  size = "md",
  className,
  label,
}: SegmentedControlProps<V>) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn(
        "inline-flex rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-0.5",
        className
      )}
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative whitespace-nowrap rounded-md font-medium transition-all",
              size === "sm"
                ? "h-7 px-2.5 text-[11.5px]"
                : "h-8 px-3 text-[12.5px]",
              active
                ? "bg-[color:var(--surface)] text-[color:var(--foreground)] shadow-sm ring-1 ring-[color:var(--border-strong)]"
                : "text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
