import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import {
  SecurityDisclaimer,
  SECURITY_DISCLAIMER,
  SECURITY_DISCLAIMER_DETAIL,
} from "@/features/security/SecurityDisclaimer";

function infoButton() {
  return screen.getByRole("button", {
    name: /more information about automated security analysis limitations/i,
  });
}

describe("SecurityDisclaimer", () => {
  it("renders the short disclaimer permanently", () => {
    render(<SecurityDisclaimer />);
    expect(screen.getByText(SECURITY_DISCLAIMER)).toBeInTheDocument();
    expect(screen.queryByText(SECURITY_DISCLAIMER_DETAIL)).not.toBeInTheDocument();
  });

  it("shows the detailed explanation on hover", async () => {
    const user = userEvent.setup();
    render(<SecurityDisclaimer />);
    await user.hover(infoButton());
    expect(screen.getByText(SECURITY_DISCLAIMER_DETAIL)).toBeInTheDocument();
  });

  it("toggles the detailed explanation on click", async () => {
    const user = userEvent.setup();
    render(<SecurityDisclaimer />);
    await user.click(infoButton());
    expect(screen.getByText(SECURITY_DISCLAIMER_DETAIL)).toBeInTheDocument();
    await user.click(infoButton());
    expect(screen.queryByText(SECURITY_DISCLAIMER_DETAIL)).not.toBeInTheDocument();
  });

  it("closes the explanation on Escape", async () => {
    const user = userEvent.setup();
    render(<SecurityDisclaimer />);
    await user.click(infoButton());
    expect(screen.getByText(SECURITY_DISCLAIMER_DETAIL)).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByText(SECURITY_DISCLAIMER_DETAIL)).not.toBeInTheDocument();
  });
});
