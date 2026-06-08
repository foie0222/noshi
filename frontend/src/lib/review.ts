// 読み取り後の確認メッセージ。要確認の件数に応じて文言を出し分ける。
// 「5か所だけ確認＝実は全部」のような矛盾コピーを避ける。

export function reviewMessage(reviewCount: number, total: number): string {
  if (reviewCount <= 0) return "読み取れました。問題なければ保存できます。";
  if (reviewCount >= total) return "うまく読み取れませんでした。各項目をご確認ください。";
  if (reviewCount > total / 2)
    return `いくつか読み取れました。残り${reviewCount}か所をご確認ください。`;
  return `ほぼ読み取れました。${reviewCount}か所だけご確認ください。`;
}
