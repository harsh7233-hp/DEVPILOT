import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AIDisclaimer, AI_DISCLAIMER } from "@/features/ai-assistant/AIDisclaimer";

describe("AIDisclaimer", () => {
  it("renders the permanent AI disclaimer", () => {
    render(<AIDisclaimer />);
    expect(screen.getByText(AI_DISCLAIMER)).toBeInTheDocument();
  });

  it("uses an accessible note role", () => {
    render(<AIDisclaimer />);
    expect(screen.getByRole("note")).toHaveTextContent(AI_DISCLAIMER);
  });
});
