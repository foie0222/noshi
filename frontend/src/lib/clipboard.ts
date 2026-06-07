// クリップボードへのコピー補助。成否を boolean で返し、失敗を握り潰さない。

export async function copyText(text: string): Promise<boolean> {
  if (!text) return false;
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // 権限拒否や非対応環境では false を返し、呼び出し側で手動コピーを促す
  }
  return false;
}
