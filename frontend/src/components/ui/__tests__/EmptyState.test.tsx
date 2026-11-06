import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EmptyState } from "@/components/ui/EmptyState";

describe("EmptyState", () => {
  it("renders icon", () => {
    render(<EmptyState icon="📦" title="T" description="D" />);
    expect(screen.getByText("📦")).toBeInTheDocument();
  });

  it("renders title", () => {
    render(<EmptyState icon="i" title="No data" description="D" />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<EmptyState icon="i" title="T" description="Nothing found" />);
    expect(screen.getByText("Nothing found")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(
      <EmptyState icon="i" title="T" description="D" action={<button>Action</button>} />
    );
    expect(screen.getByRole("button", { name: "Action" })).toBeInTheDocument();
  });

  it("does not render action when not provided", () => {
    const { container } = render(<EmptyState icon="i" title="T" description="D" />);
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  it("accepts custom className", () => {
    const { container } = render(
      <EmptyState icon="i" title="T" description="D" className="my-class" />
    );
    expect(container.firstElementChild!.className).toContain("my-class");
  });
});
