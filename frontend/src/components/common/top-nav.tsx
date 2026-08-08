import Link from "next/link";
import { Building2, ChevronRight, SearchCheck } from "lucide-react";

import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";

export function TopNav(): React.JSX.Element {
  return (
    <header className="sticky top-0 z-20 border-b border-border/70 bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-4">
          <Link className="flex items-center gap-3" href="/">
            <div className="rounded-2xl bg-primary p-2 text-primary-foreground">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-[0.2em] text-muted-foreground">
                REAL ESTATE ANALYZER
              </div>
              <div className="text-base font-semibold text-foreground">
                Investment Decision Workspace
              </div>
            </div>
          </Link>
          <StatusBadge tone="neutral">Demo</StatusBadge>
        </div>

        <nav className="hidden items-center gap-2 md:flex">
          <Button asChild variant="ghost">
            <Link href="/">New Analysis</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link href="/">
              Start Workflow
              <ChevronRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </nav>

        <Button className="w-full sm:w-auto" variant="outline">
          <SearchCheck className="mr-2 h-4 w-4" />
          Backend Connected
        </Button>

        <nav className="flex w-full items-center gap-2 md:hidden">
          <Button asChild className="flex-1" variant="ghost">
            <Link href="/">New Analysis</Link>
          </Button>
          <Button asChild className="flex-1">
            <Link href="/">
              Start Workflow
              <ChevronRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
