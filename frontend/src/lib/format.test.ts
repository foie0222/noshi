import { describe, expect, it } from "vitest";
import { daysLeftLabel, diffLabel, statusLabel, summarize, yen } from "./format";

describe("残日数の表示", () => {
  it("残日数が正なら「のこり◯日」と表示することを検証する", () => {
    expect(daysLeftLabel(5)).toBe("のこり5日");
  });
  it("残日数が0なら「きょうが期限」と表示することを検証する", () => {
    expect(daysLeftLabel(0)).toBe("きょうが期限");
  });
  it("残日数が負なら「期限超過」と表示することを検証する", () => {
    expect(daysLeftLabel(-2)).toBe("期限超過");
  });
  it("期限なし(null)は空文字を返すことを検証する", () => {
    expect(daysLeftLabel(null)).toBe("");
  });
});

describe("ステータス表示", () => {
  it("英語のステータス値を日本語ラベルに変換することを検証する", () => {
    expect(statusLabel("received")).toBe("受領");
    expect(statusLabel("considering")).toBe("対応中"); // #4: 検討中→対応中（キーは据え置き）
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
