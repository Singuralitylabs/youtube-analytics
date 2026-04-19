import * as React from "react";

import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-3 py-1 text-[13px] text-[color:var(--foreground)] transition-all file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-[color:var(--foreground)] placeholder:text-[color:var(--muted-foreground)] hover:border-[color:var(--border-strong)] focus-visible:border-[color:var(--primary)] focus-visible:shadow-[0_0_0_4px_var(--primary-soft)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
