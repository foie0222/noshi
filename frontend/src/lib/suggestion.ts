// 提案カードの表示用純関数。価格は取得時点つき、マスク時は金額帯の目安に落とす（楽天規約対応）。

import type { Suggestion } from "../types";

export function priceLine(s: Suggestion): string {
  if (s.price == null || !s.price_fetched_at) return `${s.price_band} 目安`;
  // 表示は常に日本時間（実行マシンのTZに依存させない。CI/ローカル差異の排除）
  const d = new Date(s.price_fetched_at);
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Tokyo",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  const stamp = `${get("month")}/${get("day")} ${get("hour")}:${get("minute")}`;
  return `¥${s.price.toLocaleString()}（${stamp}時点）`;
}
