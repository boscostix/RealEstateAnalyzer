import { cn } from "@/lib/utils";

type LoadingSkeletonProps = {
  className?: string;
};

export function LoadingSkeleton({ className }: LoadingSkeletonProps): React.JSX.Element {
  return <div className={cn("animate-pulse rounded-xl bg-muted", className)} />;
}
