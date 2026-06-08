// 表示用フォーマット（純粋関数）

const STATUS_LABELS: Record<string, string> = {
  received: "受領",
  considering: "検討中",
  done: "完了",
};

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
