import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PropertyHistoryFlow } from "@/components/workflow/property-history-flow";
import { AnalysisReportFlow } from "@/components/workflow/analysis-report-flow";
import {
  demoAnalysisListResponse,
  demoCompletedAnalysis,
  demoPropertyResponse,
} from "@/lib/demo-fixtures";

const mockPush = vi.fn();
const mockReplace = vi.fn();
const mockUseParams = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => mockUseParams(),
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
}));

vi.mock("@/lib/api/properties", () => ({
  getProperty: vi.fn(),
  listPropertyAnalyses: vi.fn(),
}));

vi.mock("@/lib/api/analyses", () => ({
  getAnalysis: vi.fn(),
  rerunAnalysis: vi.fn(),
}));

async function renderWithQueryClient(element: ReactElement): Promise<void> {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}

describe("frontend demo happy path", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockReplace.mockReset();
    mockUseParams.mockReset();
  });

  it("renders persisted property history and report views from the demo fixtures", async () => {
    const propertiesApi = await import("@/lib/api/properties");
    const analysesApi = await import("@/lib/api/analyses");

    (propertiesApi.getProperty as Mock).mockResolvedValue(demoPropertyResponse);
    (propertiesApi.listPropertyAnalyses as Mock).mockResolvedValue(demoAnalysisListResponse);
    (analysesApi.getAnalysis as Mock).mockResolvedValue({
      success: true,
      analysis: demoCompletedAnalysis,
    });

    mockUseParams.mockReturnValue({ propertyId: demoPropertyResponse.property.id });
    await renderWithQueryClient(<PropertyHistoryFlow />);

    expect(await screen.findByText("123 Main St, Dallas, TX 75001")).toBeInTheDocument();
    expect(screen.getByText("Latest analysis summary")).toBeInTheDocument();
    expect(screen.getAllByText("completed")).not.toHaveLength(0);
    expect(screen.getByText("Open latest report")).toBeInTheDocument();
    expect(screen.getByText("Analysis history")).toBeInTheDocument();
    expect(screen.getAllByText("v3")).not.toHaveLength(0);

    mockUseParams.mockReturnValue({ analysisId: demoCompletedAnalysis.id });
    await renderWithQueryClient(<AnalysisReportFlow />);

    expect(
      await screen.findByRole("heading", {
        level: 3,
        name: "Negotiate",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Executive Summary")).toBeInTheDocument();
    expect(screen.getByText("Offer Range")).toBeInTheDocument();
    expect(screen.getByText(/rental comparables/i)).toBeInTheDocument();
    expect(screen.getByText(/evidence.*sources/i)).toBeInTheDocument();
    expect(screen.getAllByText("Works only with a lower purchase price.")).not.toHaveLength(0);
  });
});
