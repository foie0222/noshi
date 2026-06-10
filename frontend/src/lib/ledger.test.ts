import { describe, expect, it } from "vitest";
import type { GiftRecord } from "../types";
import { filterSortRecords, LEDGER_DEFAULT } from "./ledger";

function rec(p: Partial<GiftRecord>): GiftRecord {
  return {
    id: Math.random().toString(),
    user_id: "u",
    party_name: "",
    amount: 0,
    purpose: "",
    direction: "received",
    occurred_at: "",
    item: "",
    relationship: "",
    memo: "",
    ...p,
  };
}

const data: GiftRecord[] = [
  rec({
    party_name: "佐藤",
    purpose: "出産祝い",
    amount: 30000,
    direction: "received",
    occurred_at: "2026-05-01",
  }),
  rec({
    party_name: "田中",
    purpose: "結婚祝い",
    amount: 50000,
    direction: "given",
    occurred_at: "2026-03-01",
  }),
  rec({
    party_name: "佐藤",
    purpose: "香典",
    amount: 10000,
    direction: "received",
    occurred_at: "2026-06-01",
  }),
];

describe("台帳の検索・絞り込み・並べ替え（#51）", () => {
  it("既定は日付の新しい順であることを検証する", () => {
    const out = filterSortRecords(data, LEDGER_DEFAULT);
    expect(out.map((r) => r.occurred_at)).toEqual(["2026-06-01", "2026-05-01", "2026-03-01"]);
  });

  it("相手名・用途で検索できることを検証する", () => {
    expect(filterSortRecords(data, { ...LEDGER_DEFAULT, query: "佐藤" })).toHaveLength(2);
    expect(filterSortRecords(data, { ...LEDGER_DEFAULT, query: "結婚" })).toHaveLength(1);
  });

  it("品物名でも検索できることを検証する", () => {
    const withItem = [...data, rec({ party_name: "鈴木", purpose: "快気祝い", item: "メガネ" })];
    expect(filterSortRecords(withItem, { ...LEDGER_DEFAULT, query: "メガネ" })).toHaveLength(1);
  });

  it("方向で絞り込めることを検証する", () => {
    expect(filterSortRecords(data, { ...LEDGER_DEFAULT, direction: "given" })).toHaveLength(1);
    expect(filterSortRecords(data, { ...LEDGER_DEFAULT, direction: "received" })).toHaveLength(2);
  });

  it("金額の高い順に並べ替えできることを検証する", () => {
    const out = filterSortRecords(data, { ...LEDGER_DEFAULT, sort: "amount_desc" });
    expect(out.map((r) => r.amount)).toEqual([50000, 30000, 10000]);
  });

  it("日付の古い順に並べ替えできることを検証する", () => {
    const out = filterSortRecords(data, { ...LEDGER_DEFAULT, sort: "date_asc" });
    expect(out.map((r) => r.occurred_at)).toEqual(["2026-03-01", "2026-05-01", "2026-06-01"]);
  });
});
