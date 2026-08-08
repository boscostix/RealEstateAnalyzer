"use client";

import { StatusBadge } from "@/components/common/status-badge";
import { verificationStatusTone } from "@/lib/property-workflow";
import type { VerificationStatus } from "@/lib/api/types";

type VerificationStatusBadgeProps = {
  status: VerificationStatus;
};

export function VerificationStatusBadge({
  status,
}: VerificationStatusBadgeProps): React.JSX.Element {
  return (
    <StatusBadge tone={verificationStatusTone(status)}>
      {status.replace("_", " ")}
    </StatusBadge>
  );
}
