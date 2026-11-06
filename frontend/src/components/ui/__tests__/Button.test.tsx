import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Button } from "@/components/ui/Button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });

  it("applies primary variant by default", () => {
    render(<Button>Primary</Button>);
    expect(screen.getByRole("button").className).toContain("bg-emerald-600");
  });

  it("applies secondary variant", () => {
    render(<Button variant="secondary">Secondary</Button>);
    const btn = screen.getByRole("button");
    expect(btn.style.background).toBe("var(--btn-secondary-bg)");
    expect(btn.style.color).toBe("var(--btn-secondary-text)");
  });

  it("applies ghost variant", () => {
    render(<Button variant="ghost">Ghost</Button>);
    const btn = screen.getByRole("button");
    expect(btn.style.color).toBe("var(--btn-ghost-text)");
  });

  it("applies danger variant", () => {
    render(<Button variant="danger">Danger</Button>);
    expect(screen.getByRole("button").className).toContain("text-red-700");
  });

  it("applies sm size", () => {
    render(<Button size="sm">Small</Button>);
    expect(screen.getByRole("button").className).toContain("text-xs");
  });

  it("applies md size", () => {
    render(<Button size="md">Medium</Button>);
    expect(screen.getByRole("button").className).toContain("text-sm");
  });

  it("applies lg size", () => {
    render(<Button size="lg">Large</Button>);
    expect(screen.getByRole("button").className).toContain("text-sm");
  });

  it("calls onClick when clicked", () => {
    const fn = vi.fn();
    render(<Button onClick={fn}>Click</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(fn).toHaveBeenCalledOnce();
  });

  it("respects disabled prop", () => {
    const fn = vi.fn();
    render(<DisabledButton onClick={fn} />);
    fireEvent.click(screen.getByRole("button"));
    expect(fn).not.toHaveBeenCalled();
  });

  it("passes HTML button attributes", () => {
    render(<Button type="submit">Submit</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
  });
});

function DisabledButton({ onClick }: { onClick: () => void }) {
  return <Button disabled onClick={onClick}>Disabled</Button>;
}
