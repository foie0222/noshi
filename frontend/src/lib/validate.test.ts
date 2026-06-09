import { describe, expect, it } from "vitest";
import { hasErrors, recordErrors } from "./validate";

describe("記録入力の検証（#50）", () => {
  it("正しい入力ではエラーが無いことを検証する", () => {
    const e = recordErrors({ amount: "10000", purpose: "出産祝い", partyId: "p1" });
    expect(hasErrors(e)).toBe(false);
  });

  it("金額が空/0/非数値なら amount エラーを返すことを検証する", () => {
    expect(recordErrors({ amount: "", purpose: "出産祝い", partyId: "p1" }).amount).toBeTruthy();
    expect(recordErrors({ amount: "0", purpose: "出産祝い", partyId: "p1" }).amount).toBeTruthy();
    expect(recordErrors({ amount: "abc", purpose: "出産祝い", partyId: "p1" }).amount).toBeTruthy();
  });

  it("用途が空なら purpose エラー、相手未選択なら party エラーを返すことを検証する", () => {
    const e = recordErrors({ amount: "10000", purpose: "", partyId: "" });
    expect(e.purpose).toBeTruthy();
    expect(e.party).toBeTruthy();
    expect(hasErrors(e)).toBe(true);
  });
});
