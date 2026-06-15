import { describe, expect, it } from "vitest";
import { emptyManualDraft } from "./draft";

describe("emptyManualDraft（撮影なし手入力の空ドラフト）", () => {
  it("種類は撮影フローと揃えて『もらった』(received) を初期選択にすることを検証する", () => {
    expect(emptyManualDraft().direction).toBe("received");
  });

  it("各フィールドが空で初期化されることを検証する", () => {
    const d = emptyManualDraft();
    expect(d.amount).toBe("");
    expect(d.party_name).toBe("");
    expect(d.relationship).toBe("");
    expect(d.purpose).toBe("");
    expect(d.occurred_at).toBe("");
    expect(d.item).toBe("");
    expect(d.party_id).toBe("");
    expect(d.image).toBe("");
    expect(d.field_review).toEqual({});
  });

  it("呼び出しごとに独立したオブジェクトを返すことを検証する", () => {
    expect(emptyManualDraft()).not.toBe(emptyManualDraft());
  });
});
