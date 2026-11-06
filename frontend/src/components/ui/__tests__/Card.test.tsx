import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Card } from "@/components/ui/Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Content here</Card>);
    expect(screen.getByText("Content here")).toBeInTheDocument();
  });

  it("applies md padding by default", () => {
    render(<Card>P</Card>);
    expect(screen.getByText("P")).toHaveClass("p-5");
  });

  it("applies sm padding", () => {
    render(<Card padding="sm">P</Card>);
    expect(screen.getByText("P")).toHaveClass("p-4");
  });

  it("applies lg padding", () => {
    render(<Card padding="lg">P</Card>);
    expect(screen.getByText("P")).toHaveClass("p-6");
  });

  it("applies no padding", () => {
    render(<Card padding="none">P</Card>);
    const el = screen.getByText("P");
    expect(el).not.toHaveClass("p-4", "p-5", "p-6");
  });

  it("calls onClick when clickable", () => {
    const fn = vi.fn();
    render(<Card onClick={fn}>Clickable</Card>);
    fireEvent.click(screen.getByText("Clickable"));
    expect(fn).toHaveBeenCalledOnce();
  });

  it("adds cursor-pointer when onClick provided", () => {
    render(<Card onClick={() => {}}>C</Card>);
    expect(screen.getByText("C")).toHaveClass("cursor-pointer");
  });

  it("accepts custom className", () => {
    render(<Card className="custom">C</Card>);
    expect(screen.getByText("C")).toHaveClass("custom");
  });
});
