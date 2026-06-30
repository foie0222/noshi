import { describe, expect, it } from "vitest";
import type { GiftRecord } from "../types";
import { filterReturnRecords, isValidReturnAmount } from "./return";

function rec(p: Partial<GiftRecord>): GiftRecord {
  return {
    id: Math.random().toString(),
    user_id: "u",
    party_name: "",
    amount: 0,
    purpose: "",
    direction: "given",
    occurred_at: "",
    item: "",
    relationship: "",
    memo: "",
    ...p,
  };
}

describe("isValidReturnAmount — saveReturn の early-return ガード", () => {
  it("金額が空なら無効（saveReturn は API を呼ばず early-return する）", () => {
    expect(isValidReturnAmount("")).toBe(false);
    expect(isValidReturnAmount("  ")).toBe(false);
  });

  it("金額が 0 以下なら無効（saveReturn は API を呼ばず early-return する）", () => {
    expect(isValidReturnAmount("0")).toBe(false);
    expect(isValidReturnAmount("-500")).toBe(false);
  });

  it("正の金額なら有効（saveReturn は API 呼び出しに進む）", () => {
    expect(isValidReturnAmount("1000")).toBe(true);
    expect(isValidReturnAmount("1")).toBe(true);
  });
});

describe("filterReturnRecords — loadReturnRecords / saveReturn 後の returnRecords 更新", () => {
  it("return_for_id が一致するレコードのみ返す", () => {
    const records = [
      rec({ id: "r1", return_for_id: "target-1" }),
      rec({ id: "r2", return_for_id: "target-2" }),
      rec({ id: "r3", return_for_id: "target-1" }),
    ];
    const result = filterReturnRecords(records, "target-1");
    expect(result).toHaveLength(2);
    expect(result.map((r) => r.id)).toEqual(["r1", "r3"]);
  });

  it("成功後 returnRecords が return_for_id でフィルタされたレコードで更新される（一致なしは空配列）", () => {
    const records = [rec({ id: "r1", return_for_id: "other" })];
    expect(filterReturnRecords(records, "target-1")).toHaveLength(0);
  });

  it("return_for_id 未設定のレコードは除外される", () => {
    const records = [
      rec({ id: "r1", return_for_id: "target-1" }),
      rec({ id: "r2" }), // return_for_id なし
    ];
    expect(filterReturnRecords(records, "target-1")).toHaveLength(1);
  });
});
