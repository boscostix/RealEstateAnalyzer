import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium uppercase tracking-[0.16em]",
  {
    variants: {
      tone: {
        neutral: "border-border bg-muted text-muted-foreground",
        success: "border-success/30 bg-success/10 text-success",
        warning: "border-warning/30 bg-warning/10 text-warning",
        danger: "border-danger/30 bg-danger/10 text-danger",
      },
    },
    defaultVariants: {
      tone: "neutral",
    },
  },
);

type StatusBadgeProps = VariantProps<typeof badgeVariants> & {
  children: string;
  className?: string;
};

export function StatusBadge({
  children,
  tone,
  className,
}: StatusBadgeProps): React.JSX.Element {
  return <span className={cn(badgeVariants({ tone }), className)}>{children}</span>;
}
