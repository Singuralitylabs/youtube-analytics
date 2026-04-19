import { cn } from "@/lib/utils";

/**
 * Panel — the workhorse content container for the dashboard.
 * Replaces shadcn's Card on pages where we want the GA-card aesthetic
 * (barely-there border, micro elevation, compact typographic hierarchy).
 */
export interface PanelProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  title?: React.ReactNode;
  eyebrow?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  /** Padded body wrapper (use false to render children flush) */
  bodyPadding?: boolean;
  bodyClassName?: string;
}

export function Panel({
  title,
  eyebrow,
  description,
  actions,
  bodyPadding = true,
  bodyClassName,
  children,
  className,
  ...props
}: PanelProps) {
  return (
    <section className={cn("ga-card overflow-hidden", className)} {...props}>
      {(title || actions || description || eyebrow) && (
        <header className="flex items-start justify-between gap-4 px-5 pt-4">
          <div>
            {eyebrow && (
              <div className="text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
                {eyebrow}
              </div>
            )}
            {title && (
              <h2 className="font-display text-[15.5px] text-[color:var(--foreground)]">
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-0.5 text-[12px] text-[color:var(--muted-foreground)]">
                {description}
              </p>
            )}
          </div>
          {actions && (
            <div className="flex shrink-0 items-center gap-2">{actions}</div>
          )}
        </header>
      )}
      <div
        className={cn(
          bodyPadding ? "p-5" : "",
          (title || actions) && bodyPadding ? "pt-4" : "",
          bodyClassName
        )}
      >
        {children}
      </div>
    </section>
  );
}
