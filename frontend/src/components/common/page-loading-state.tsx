import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

type PageLoadingStateProps = {
  title?: string;
  description?: string;
  titleWidthClassName?: string;
  lines?: number;
};

export function PageLoadingState({
  title,
  description,
  titleWidthClassName = "w-56",
  lines = 3,
}: PageLoadingStateProps): React.JSX.Element {
  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader className="gap-4">
          {title ? (
            <div className="space-y-2">
              <div className="text-lg font-semibold text-foreground">{title}</div>
              {description ? (
                <p className="text-sm text-muted-foreground">{description}</p>
              ) : null}
            </div>
          ) : (
            <>
              <LoadingSkeleton className={`h-6 ${titleWidthClassName}`} />
              <LoadingSkeleton className="h-4 w-full max-w-2xl" />
              <LoadingSkeleton className="h-4 w-full max-w-xl" />
            </>
          )}
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: lines }).map((_, index) => (
            <LoadingSkeleton className="h-24 w-full" key={index} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
