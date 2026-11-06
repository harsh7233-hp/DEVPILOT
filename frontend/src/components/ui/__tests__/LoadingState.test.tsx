import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { LoadingState } from "@/components/ui/LoadingState";

describe("LoadingState", () => {
  it("renders default message", () => {
    render(<LoadingState />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders custom message", () => {
    render(<LoadingState message="Fetching data..." />);
    expect(screen.getByText("Fetching data...")).toBeInTheDocument();
  });

  it("contains spinner element", () => {
    const { container } = render(<LoadingState />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });
});
