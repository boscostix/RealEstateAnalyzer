"use client";

import { ErrorState } from "@/components/common/error-state";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): React.JSX.Element {
  return (
    <div className="mx-auto max-w-2xl py-20">
      <ErrorState
        title="Frontend shell failed to render"
        message={error.message || "An unexpected rendering error occurred."}
        onAction={reset}
      />
    </div>
  );
}
