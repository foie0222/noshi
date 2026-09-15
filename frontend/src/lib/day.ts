/**
 * n 日前のローカル日付を `YYYY-MM-DD` で返す（`<input type="date">` にそのまま入る形）。
 *
 * UTC 変換を挟むと日本時間の夜に前日へずれるため、ローカルの年月日から組み立てる。
 * 「贈った日」を今日／昨日のチップで選べるようにするために使う。
 */
export function isoDaysAgo(n: number, today: Date = new Date()): string {
  const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - n);
  const pad = (v: number) => String(v).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
