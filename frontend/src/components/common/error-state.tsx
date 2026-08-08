import { AlertTriangle, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type ErrorStateProps = {
  title?: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function ErrorState({
  title = "Unable to load this view",
  message,
  actionLabel = "Try again",
  onAction,
}: ErrorStateProps): React.JSX.Element {
  return (
    <Card aria-live="polite" className="border-danger/20" role="alert">
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-danger/10 p-2 text-danger">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <CardTitle>{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{message}</p>
        {onAction ? (
          <Button variant="outline" onClick={onAction}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            {actionLabel}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
