import { describe, it, expect } from "vitest";
import { classNames, formatDate, riskColor, languageColor } from "@/lib/utils";

describe("classNames", () => {
  it("joins strings", () => {
    expect(classNames("a", "b", "c")).toBe("a b c");
  });

  it("filters falsy values", () => {
    expect(classNames("a", false, null, undefined, "b")).toBe("a b");
  });

  it("returns empty string for no truthy args", () => {
    expect(classNames(false, null, undefined)).toBe("");
  });
});

describe("formatDate", () => {
  it("returns 'Just now' for recent timestamps", () => {
    const now = new Date().toISOString();
    expect(formatDate(now)).toBe("Just now");
  });

  it("returns minutes ago", () => {
    const d = new Date(Date.now() - 5 * 60000).toISOString();
    expect(formatDate(d)).toBe("5m ago");
  });

  it("returns hours ago", () => {
    const d = new Date(Date.now() - 3 * 3600000).toISOString();
    expect(formatDate(d)).toBe("3h ago");
  });

  it("returns days ago", () => {
    const d = new Date(Date.now() - 4 * 86400000).toISOString();
    expect(formatDate(d)).toBe("4d ago");
  });

  it("returns formatted date for old timestamps", () => {
    const d = new Date("2020-06-15T12:00:00Z").toISOString();
    const result = formatDate(d);
    expect(result).toContain("Jun");
    expect(result).toContain("15");
    expect(result).toContain("2020");
  });
});

describe("riskColor", () => {
  it("returns emerald for low", () => {
    expect(riskColor("low")).toContain("emerald");
  });

  it("returns yellow for medium", () => {
    expect(riskColor("medium")).toContain("yellow");
  });

  it("returns orange for high", () => {
    expect(riskColor("high")).toContain("orange");
  });

  it("returns red for critical", () => {
    expect(riskColor("critical")).toContain("red");
  });
});

describe("languageColor", () => {
  it("returns blue for TypeScript", () => {
    expect(languageColor("TypeScript")).toBe("bg-blue-500");
  });

  it("returns yellow for JavaScript", () => {
    expect(languageColor("JavaScript")).toBe("bg-yellow-400");
  });

  it("returns green for Python", () => {
    expect(languageColor("Python")).toBe("bg-green-500");
  });

  it("returns zinc for unknown", () => {
    expect(languageColor("Rust")).toBe("bg-zinc-500");
  });
});
