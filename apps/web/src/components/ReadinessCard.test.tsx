import { render, screen } from "@testing-library/react";

import { ReadinessCard } from "./ReadinessCard";

describe("ReadinessCard", () => {
  it("keeps the valid not configured status visible alongside its status treatment", () => {
    render(<ReadinessCard label="Stockfish" item={{ status: "not_configured", details: "Stockfish path is not configured." }} />);

    expect(screen.getByText("not configured")).toBeVisible();
    expect(screen.getByText("not configured")).toHaveClass("status-badge--not_configured");
    expect(screen.getByText("Stockfish path is not configured.")).toBeVisible();
  });
});
