import { cn } from "@/lib/utils";

export interface PageHeaderProps {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 pb-2 sm:flex-row sm:items-end sm:justify-between",
        className
      )}
    >
      <div className="space-y-1.5">
        {eyebrow && (
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.18em] text-[color:var(--primary)]">
            {eyebrow}
          </div>
        )}
        <h1 className="font-display text-[32px] leading-[1.1] text-[color:var(--foreground)] sm:text-[36px]">
          {title}
        </h1>
        {description && (
          <p className="max-w-2xl text-[13.5px] text-[color:var(--muted-foreground)]">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      )}
    </header>
  );
}
