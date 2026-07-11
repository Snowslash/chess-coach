import { render, screen } from "@testing-library/react";

import { PrivacyNotice } from "./PrivacyNotice";

describe("PrivacyNotice", () => {
  it("states the local-only privacy boundary without promising readiness", () => {
    render(<PrivacyNotice storage="Generated reports and diagnostics stay local." />);

    expect(screen.getByText(/local-only/i)).toBeInTheDocument();
    expect(screen.getByText(/Generated reports and diagnostics stay local/i)).toBeInTheDocument();
    expect(screen.queryByText(/ready/i)).not.toBeInTheDocument();
  });
});
