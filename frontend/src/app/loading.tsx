import { LoadingSkeleton } from "@/components/common/loading-skeleton";

export default function Loading(): React.JSX.Element {
  return (
    <div className="grid gap-6">
      <LoadingSkeleton className="h-14 w-40" />
      <LoadingSkeleton className="h-48 w-full" />
      <div className="grid gap-4 md:grid-cols-3">
        <LoadingSkeleton className="h-32 w-full" />
        <LoadingSkeleton className="h-32 w-full" />
        <LoadingSkeleton className="h-32 w-full" />
      </div>
    </div>
  );
}
