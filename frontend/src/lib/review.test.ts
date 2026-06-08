import { describe, expect, it } from "vitest";
import { reviewMessage } from "./review";

describe("読み取り確認メッセージ（件数に応じた出し分け）", () => {
  it("要確認が0なら、そのまま保存できる旨を返すことを検証する", () => {
    const m = reviewMessage(0, 5);
    expect(m).toContain("保存");
    expect(m).not.toContain("確認してください");
  });

  it("要確認が少数なら「ほぼ読み取れました・N か所だけ」を返すことを検証する", () => {
    const m = reviewMessage(1, 5);
    expect(m).toContain("ほぼ読み取れました");
    expect(m).toContain("1");
    expect(m).toContain("だけ");
  });

  it("全項目が要確認なら「だけ」も「ほぼ」も使わない文言を返すことを検証する（5か所だけ＝全部の矛盾回避）", () => {
    const m = reviewMessage(5, 5);
    expect(m).not.toContain("だけ");
    expect(m).not.toContain("ほぼ読み取れました");
  });

  it("過半数が要確認なら「だけ」を使わない（多くの確認が必要な旨）ことを検証する", () => {
    const m = reviewMessage(3, 5);
    expect(m).not.toContain("だけ");
    expect(m).toContain("3");
  });
});
