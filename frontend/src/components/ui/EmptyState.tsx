import { Inbox } from "lucide-react";

import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  title?: string;
  message: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  height?: number;
}

export function EmptyState({
  title,
  message,
  icon,
  action,
  className,
  height = 200,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-[color:var(--border-strong)] bg-[color:var(--surface-2)]/40 px-6 py-8 text-center",
        className
      )}
      style={{ minHeight: height }}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[color:var(--surface)] text-[color:var(--muted-foreground)] ring-1 ring-[color:var(--border-strong)]">
        {icon ?? <Inbox className="h-4 w-4" />}
      </div>
      {title && (
        <div className="text-[13.5px] font-semibold text-[color:var(--foreground)]">
          {title}
        </div>
      )}
      <p className="max-w-xs text-[12.5px] leading-relaxed text-[color:var(--muted-foreground)]">
        {message}
      </p>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
