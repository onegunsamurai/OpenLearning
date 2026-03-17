import { vi } from "vitest";

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

import { redirect } from "next/navigation";
import DemoPage from "./page";

describe("DemoPage", () => {
  it("redirects to /demo/assess", () => {
    try {
      DemoPage();
    } catch {
      // redirect throws NEXT_REDIRECT in production; mock is a no-op
    }
    expect(redirect).toHaveBeenCalledWith("/demo/assess");
  });
});
