import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "@/components/ui/Badge";

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies default variant class", () => {
    render(<Badge>Test</Badge>);
    const el = screen.getByText("Test");
    expect(el.style.background).toBe("var(--badge-default-bg)");
    expect(el.style.color).toBe("var(--badge-default-text)");
  });

  it("applies success variant class", () => {
    render(<Badge variant="success">OK</Badge>);
    const el = screen.getByText("OK");
    expect(el.className).toContain("text-emerald-400");
  });

  it("applies warning variant class", () => {
    render(<Badge variant="warning">Warn</Badge>);
    expect(screen.getByText("Warn").className).toContain("text-yellow-400");
  });

  it("applies error variant class", () => {
    render(<Badge variant="error">Fail</Badge>);
    expect(screen.getByText("Fail").className).toContain("text-red-400");
  });

  it("applies info variant class", () => {
    render(<Badge variant="info">Info</Badge>);
    expect(screen.getByText("Info").className).toContain("text-blue-400");
  });

  it("accepts custom className", () => {
    render(<Badge className="my-class">X</Badge>);
    expect(screen.getByText("X").className).toContain("my-class");
  });

  it("renders as span element", () => {
    render(<Badge>S</Badge>);
    expect(screen.getByText("S").tagName).toBe("SPAN");
  });
});
