import type { GiftRecord } from "../types";

/**
 * お返しフォームの金額入力が保存可能かを確認する。
 * 空文字・空白のみ・0以下は無効とし、API を呼ばず early-return するためのガード。
 */
export function isValidReturnAmount(amountStr: string): boolean {
  if (!amountStr.trim()) return false;
  return Number(amountStr) > 0;
}

/**
 * 台帳レコードから指定した記録へのお返し（return_for_id 一致）のみ抽出する。
 * loadReturnRecords / saveReturn 後の returnRecords 更新に使う。
 */
export function filterReturnRecords(records: GiftRecord[], returnForId: string): GiftRecord[] {
  return records.filter((rec) => rec.return_for_id === returnForId);
}
