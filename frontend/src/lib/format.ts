// 表示用フォーマット（純粋関数）

// お返しの状態: 受領 → 対応中（発注・手配・準備中）→ 完了（お渡し済み）（#4）。
// 内部キー considering は据え置き、表示名のみ「対応中」に（データ移行不要）。
const STATUS_LABELS: Record<string, string> = {
  received: "受領",
  considering: "対応中",
  done: "完了",
};

// 既に付いている敬称（重ねない）。法人の「御中」も対象（#49）。
const _HONORIFIC = /(様|さん|くん|君|ちゃん|殿|御中)$/;

/** 名前に「様」を付ける。既に敬称が付く・空文字なら二重付与しない（#49）。 */
export function withHonor(name: string): string {
  const n = (name || "").trim();
  if (!n) return "";
  return _HONORIFIC.test(n) ? n : `${n} 様`;
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function daysLeftLabel(days: number | null): string {
  if (days === null || days === undefined) return "";
  if (days > 0) return `のこり${days}日`;
  if (days === 0) return "きょうが期限";
  return "期限超過";
}

export function yen(n: number): string {
  return `¥${n.toLocaleString("ja-JP")}`;
}

export function diffLabel(n: number): string {
  const sign = n >= 0 ? "+" : "-";
  return sign + yen(Math.abs(n));
}

export interface RecordLike {
  amount: number;
  direction: string;
}

export function summarize(records: RecordLike[]): {
  received: number;
  given: number;
  diff: number;
} {
  let received = 0;
  let given = 0;
  for (const r of records) {
    if (r.direction === "received") received += r.amount;
    else if (r.direction === "given") given += r.amount;
  }
  return { received, given, diff: received - given };
}
