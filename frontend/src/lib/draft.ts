import type { Draft } from "../types";

/**
 * 撮影なしの手入力で開く空の下書き（副導線、#39）。
 * 種類は撮影フローと揃えて「もらった」(received) を初期選択にする
 * （あげた/もらったどちらも確認画面で変更可）。
 */
export function emptyManualDraft(): Draft {
  return {
    amount: "",
    party_name: "",
    relationship: "",
    purpose: "",
    occurred_at: "",
    direction: "received",
    field_review: {},
    image: "",
    party_id: "",
    item: "",
  };
}
