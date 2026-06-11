import { describe, expect, it } from "vitest";
import type { Suggestion } from "../types";
import { priceLine } from "./suggestion";

const base: Suggestion = {
  title: "今治タオル",
  summary: "上質で人気です",
  price_band: "〜¥9,999",
  external_ref: "https://hb.afl.rakuten.co.jp/x",
};

describe("priceLine", () => {
  it("価格があれば金額と取得時点を出す", () => {
    expect(priceLine({ ...base, price: 4980, price_fetched_at: "2026-06-11T05:02:00+09:00" })).toBe(
      "¥4,980（6/11 5:02時点）",
    );
  });
  it("価格がなければ金額帯の目安に落ちる", () => {
    expect(priceLine(base)).toBe("〜¥9,999 目安");
  });
});
