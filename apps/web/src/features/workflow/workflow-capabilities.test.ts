import { browserWorkflowCapabilities } from "./workflow-capabilities";

describe("browser workflow capabilities", () => {
  it("uses typed project-relative path fields without native browsing affordances", () => {
    expect(browserWorkflowCapabilities).toEqual({
      pathInput: "project-relative-text",
      canChoosePath: false,
      canOpenOutput: false,
    });
  });
});
