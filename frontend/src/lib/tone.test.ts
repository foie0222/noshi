import { describe, it, expect } from "vitest";
import { toneOf } from "./tone";

describe("弔事/慶事トーン分類", () => {
  it("香典・御霊前・法事などの弔事は mourning に分類することを検証する", () => {
    for (const p of ["香典", "御霊前", "法事", "弔慰金"]) {
      expect(toneOf(p)).toBe("mourning");
    }
  });
  it("出産祝い・結婚祝いなどの慶事は celebration に分類することを検証する", () => {
    for (const p of ["出産祝い", "結婚祝い", "入学祝い"]) {
      expect(toneOf(p)).toBe("celebration");
    }
  });
});
