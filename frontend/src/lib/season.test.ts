import { describe, expect, it } from "vitest";
import { seasonNudge, seasonOf } from "./season";

describe("季節判定", () => {
  it("6〜8月はお中元(ochugen)と判定することを検証する", () => {
    for (const m of [6, 7, 8]) expect(seasonOf(m)).toBe("ochugen");
  });
  it("11月はお歳暮(oseibo)と判定することを検証する", () => {
    expect(seasonOf(11)).toBe("oseibo");
  });
  it("12月と1月は年始(newyear)を優先することを検証する（お歳暮と重なる12月も年始）", () => {
    expect(seasonOf(12)).toBe("newyear");
    expect(seasonOf(1)).toBe("newyear");
  });
  it("該当しない月はnoneと判定することを検証する", () => {
    for (const m of [2, 3, 4, 5, 9, 10]) expect(seasonOf(m)).toBe("none");
  });
  it("季節に応じたナッジ文を返し、noneは空文字であることを検証する", () => {
    expect(seasonNudge("ochugen")).toContain("お中元");
    expect(seasonNudge("none")).toBe("");
  });
});
