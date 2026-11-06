import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ErrorState } from "@/components/ui/ErrorState";

describe("ErrorState", () => {
  it("renders default title", () => {
    render(<ErrorState message="err" />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders custom title", () => {
    render(<ErrorState title="Custom Title" message="err" />);
    expect(screen.getByText("Custom Title")).toBeInTheDocument();
  });

  it("renders error message", () => {
    render(<ErrorState message="Network timeout" />);
    expect(screen.getByText("Network timeout")).toBeInTheDocument();
  });

  it("renders retry button when onRetry provided", () => {
    render(<ErrorState message="err" onRetry={() => {}} />);
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("does not render retry button without onRetry", () => {
    const { container } = render(<ErrorState message="err" />);
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  it("calls onRetry when retry clicked", () => {
    const fn = vi.fn();
    render(<ErrorState message="err" onRetry={fn} />);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(fn).toHaveBeenCalledOnce();
  });
});
