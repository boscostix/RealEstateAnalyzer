import type { ReactNode } from "react";

import { TopNav } from "@/components/common/top-nav";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps): React.JSX.Element {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNav />
      <main className="relative">
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-[520px] bg-grid-fade bg-[size:40px_40px] [mask-image:linear-gradient(to_bottom,white,transparent)]"
        />
        <div className="relative mx-auto max-w-7xl px-6 py-10">{children}</div>
      </main>
    </div>
  );
}
