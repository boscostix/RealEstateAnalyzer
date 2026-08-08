import Link from "next/link";

import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function PropertyAssumptionsPage(): React.JSX.Element {
  return (
    <Card className="mx-auto max-w-3xl">
      <CardHeader className="gap-4">
        <div className="flex items-center gap-3">
          <StatusBadge tone="success">Ready for assumptions</StatusBadge>
        </div>
        <CardTitle className="text-3xl">
          Property verification is complete and the workflow can move forward.
        </CardTitle>
        <CardDescription className="text-base leading-7">
          This phase stops at the assumptions handoff. The next milestone phases will use the
          verified property snapshot on this record to collect assumptions and start analyses.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row">
        <Button asChild size="lg">
          <Link href="/">Start another property</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
