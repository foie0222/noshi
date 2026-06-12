import { describe, expect, it } from "vitest";
import { legalDocFromPath } from "./legal";

describe("法的文書の直URL（#155）", () => {
  it("/privacy /terms /operator が各文書キーに解決されることを検証する", () => {
    expect(legalDocFromPath("/privacy")).toBe("privacy");
    expect(legalDocFromPath("/terms")).toBe("terms");
    expect(legalDocFromPath("/operator")).toBe("operator");
  });
  it("対象外のパスは null になることを検証する", () => {
    expect(legalDocFromPath("/")).toBeNull();
    expect(legalDocFromPath("/ledger")).toBeNull();
    expect(legalDocFromPath("/privacy/extra")).toBeNull();
  });
});
