import React from "react";
import { render, screen } from "@testing-library/react";

import { StatusBadge } from "@/components/common/status-badge";

describe("StatusBadge", () => {
  it("renders its label", () => {
    render(<StatusBadge tone="success">Completed</StatusBadge>);

    expect(screen.getByText("Completed")).toBeInTheDocument();
  });
});
