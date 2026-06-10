// 台帳の検索・絞り込み・並べ替え（#51）。純粋関数でクライアント側で適用する。

import type { Direction, GiftRecord } from "../types";

export type LedgerSort = "date_desc" | "date_asc" | "amount_desc";
export type LedgerDir = "all" | Direction;

export interface LedgerView {
  query: string;
  direction: LedgerDir;
  sort: LedgerSort;
}

export const LEDGER_DEFAULT: LedgerView = { query: "", direction: "all", sort: "date_desc" };

/** 検索（相手名・用途）→ 方向で絞り込み → 並べ替え、の順で適用する。 */
export function filterSortRecords(records: GiftRecord[], v: LedgerView): GiftRecord[] {
  const q = v.query.trim().toLowerCase();
  let out = records.filter((r) => {
    if (v.direction !== "all" && r.direction !== v.direction) return false;
    if (!q) return true;
    return (
      r.party_name.toLowerCase().includes(q) ||
      r.purpose.toLowerCase().includes(q) ||
      r.item.toLowerCase().includes(q)
    );
  });
  out = [...out].sort((a, b) => {
    if (v.sort === "amount_desc") return b.amount - a.amount;
    // 日付順。空の日付は末尾に寄せる。
    const da = a.occurred_at || "";
    const db = b.occurred_at || "";
    if (v.sort === "date_asc") return cmpDateAsc(da, db);
    return cmpDateAsc(db, da); // date_desc
  });
  return out;
}

function cmpDateAsc(a: string, b: string): number {
  if (a === b) return 0;
  if (!a) return 1; // 空は末尾
  if (!b) return -1;
  return a < b ? -1 : 1;
}
