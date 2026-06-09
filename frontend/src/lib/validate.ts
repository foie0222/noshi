// 記録入力の検証（#50）。エラーは項目ごとにインライン表示するため map で返す。

export interface RecordErrors {
  amount?: string;
  purpose?: string;
  party?: string;
}

/** 金額(文字列)・用途・相手ID を検証し、問題のある項目だけメッセージを返す。 */
export function recordErrors(input: {
  amount: string;
  purpose: string;
  partyId: string;
}): RecordErrors {
  const errors: RecordErrors = {};
  const n = Number(input.amount);
  if (!input.amount.trim() || Number.isNaN(n) || n <= 0) {
    errors.amount = "金額は1円以上で入力してください。";
  }
  if (!input.purpose.trim()) {
    errors.purpose = "用途を選んでください。";
  }
  if (!input.partyId) {
    errors.party = "お相手を選んでください。";
  }
  return errors;
}

export function hasErrors(e: RecordErrors): boolean {
  return Object.keys(e).length > 0;
}
