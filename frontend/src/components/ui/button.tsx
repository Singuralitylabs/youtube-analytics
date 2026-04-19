import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-[13px] font-semibold transition-all duration-150 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--primary-soft)] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-[color:var(--primary)] text-[color:var(--primary-foreground)] shadow-[0_1px_0_rgba(15,23,42,0.04),0_4px_12px_-4px_rgba(26,115,232,0.45)] hover:bg-[#1763cc] active:bg-[#155bb8]",
        destructive:
          "bg-[color:var(--danger)] text-white shadow-sm hover:bg-[#c4291e]",
        outline:
          "border border-[color:var(--border-strong)] bg-[color:var(--surface)] text-[color:var(--foreground)] hover:bg-[color:var(--surface-2)]",
        secondary:
          "bg-[color:var(--surface-2)] text-[color:var(--foreground)] hover:bg-[color:var(--muted)]",
        ghost:
          "text-[color:var(--muted-foreground)] hover:bg-[color:var(--surface-2)] hover:text-[color:var(--foreground)]",
        soft:
          "bg-[color:var(--primary-soft)] text-[color:var(--primary)] hover:bg-[#d6e6fc]",
        link:
          "text-[color:var(--primary)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-3.5",
        sm: "h-8 px-2.5 text-[12px] [&_svg]:size-3.5",
        lg: "h-10 px-5 text-[13.5px]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
