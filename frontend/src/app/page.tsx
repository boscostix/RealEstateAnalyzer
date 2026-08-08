import { ArrowRight, Building2, DatabaseZap, ShieldCheck } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getApiBaseUrl } from "@/lib/env";

const workflowSteps = [
  "Extract listing data",
  "Verify important property fields",
  "Set underwriting assumptions",
  "Run persisted analysis",
  "Review the investment memo",
];

export default function HomePage(): React.JSX.Element {
  return (
    <div className="grid gap-8">
      <section className="grid gap-8 lg:grid-cols-[1.45fr_0.95fr]">
        <Card className="overflow-hidden border-border/70 bg-[radial-gradient(circle_at_top_left,rgba(191,219,254,0.35),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))]">
          <CardHeader className="gap-5">
            <div className="flex items-center gap-3">
              <StatusBadge tone="success">Phase 1 Foundation</StatusBadge>
              <span className="text-sm text-muted-foreground">
                Backend: {getApiBaseUrl()}
              </span>
            </div>
            <div className="max-w-3xl space-y-4">
              <CardTitle className="text-4xl leading-tight md:text-5xl">
                Structured property diligence for real estate investment decisions.
              </CardTitle>
              <CardDescription className="max-w-2xl text-base leading-7 text-muted-foreground">
                Paste a property listing and move through extraction, verification,
                underwriting, research, AI review, and investment committee output inside a
                purpose-built analysis workspace.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <label className="block text-sm font-medium text-foreground" htmlFor="listing-url">
                Property listing URL
              </label>
              <div className="flex flex-col gap-3 md:flex-row">
                <Input
                  defaultValue="https://www.zillow.com/homedetails/example"
                  id="listing-url"
                  placeholder="Paste a Zillow or Redfin URL"
                />
                <Button className="md:min-w-48" disabled size="lg">
                  Analyze Property
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                URL submission and extraction integration start in Phase 2. Phase 1 wires the
                layout, API client, validation foundation, and common UI system.
              </p>
            </div>

            <div className="rounded-2xl border border-border/70 bg-background/70 p-5">
              <div className="mb-4 text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Workflow
              </div>
              <ol className="space-y-3">
                {workflowSteps.map((step, index) => (
                  <li className="flex items-center gap-3 text-sm text-foreground" key={step}>
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                      {index + 1}
                    </div>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl">
                <Building2 className="h-5 w-5 text-primary" />
                Frontend Foundation
              </CardTitle>
              <CardDescription>
                Next.js App Router, TypeScript, Tailwind, shadcn-style primitives, API
                client centralization, and responsive layout tokens.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl">
                <DatabaseZap className="h-5 w-5 text-primary" />
                Persisted Backend Ready
              </CardTitle>
              <CardDescription>
                Stable property IDs, stable analysis IDs, polling-friendly progress states,
                immutable snapshots, history, and rerun endpoints are already available.
              </CardDescription>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-xl">
                <ShieldCheck className="h-5 w-5 text-primary" />
                POC Guardrails
              </CardTitle>
              <CardDescription>
                No secrets in the browser, no duplicated underwriting math, and no direct
                OpenAI calls from the frontend.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <EmptyState
          message="Workflow pages for verification, assumptions, progress, and report rendering are introduced incrementally in the next phases."
          title="Interactive analysis flow not wired yet"
        />
        <Card>
          <CardHeader>
            <CardTitle>Phase 1 Deliverables</CardTitle>
            <CardDescription>
              This milestone pass establishes the UI and integration base we will build on.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-3 text-sm text-muted-foreground">
              <li>Typed API client with timeout and structured error normalization</li>
              <li>Shared money, date, and percentage formatters</li>
              <li>Responsive shell, navigation, loading states, and reusable cards</li>
              <li>TanStack Query provider for later polling and mutations</li>
              <li>Testing, linting, typecheck, and production build configuration</li>
            </ul>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
