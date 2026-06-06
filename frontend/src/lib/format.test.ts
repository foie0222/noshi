import { describe, it, expect } from "vitest";
import { yen, diffLabel, summarize, statusLabel } from "./format";

describe("ステータス表示", () => {
  it("英語のステータス値を日本語ラベルに変換することを検証する", () => {
    expect(statusLabel("received")).toBe("受領");
    expect(statusLabel("considering")).toBe("検討中");
    expect(statusLabel("done")).toBe("完了");
  });

  it("未知のステータスはそのまま返すことを検証する", () => {
    expect(statusLabel("unknown")).toBe("unknown");
  });
});

describe("表示フォーマット", () => {
  it("金額を円記号つきの3桁区切りで表示することを検証する", () => {
    expect(yen(30000)).toBe("¥30,000");
  });

  it("差分が正なら+符号つき、負なら-符号つきで表示することを検証する", () => {
    expect(diffLabel(45000)).toBe("+¥45,000");
    expect(diffLabel(-1000)).toBe("-¥1,000");
  });

  it("レコード配列から もらった/あげた/差分 の合計を集計することを検証する", () => {
    const recs = [
      { amount: 30000, direction: "received" },
      { amount: 5000, direction: "received" },
      { amount: 20000, direction: "given" },
    ];
    const s = summarize(recs);
    expect(s.received).toBe(35000);
    expect(s.given).toBe(20000);
    expect(s.diff).toBe(15000);
  });
});
