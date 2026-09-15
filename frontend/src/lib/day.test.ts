import { describe, expect, it } from "vitest";
import { isoDaysAgo } from "./day";

describe("isoDaysAgo（贈った日のチップ用の日付）", () => {
  it("0日前は当日の YYYY-MM-DD を返す", () => {
    expect(isoDaysAgo(0, new Date(2026, 8, 15))).toBe("2026-09-15");
  });
  it("1日前は前日になる", () => {
    expect(isoDaysAgo(1, new Date(2026, 8, 15))).toBe("2026-09-14");
  });
  it("月をまたいでも前月の末日に正しく戻る", () => {
    expect(isoDaysAgo(1, new Date(2026, 8, 1))).toBe("2026-08-31");
  });
  it("年をまたいでも前年の大晦日に正しく戻る", () => {
    expect(isoDaysAgo(1, new Date(2027, 0, 1))).toBe("2026-12-31");
  });
  it("月日は2桁でゼロ埋めする（date 入力がそのまま受け取れる形）", () => {
    expect(isoDaysAgo(0, new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});
