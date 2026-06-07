// 撮影画像の検証（BR-VAL-1: 許可形式・最大サイズ）。

export const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10MB
const ALLOWED = ["image/jpeg", "image/jpg", "image/png", "image/heic", "image/heif", "image/webp"];

/** 画像ファイルを検証し、問題があればユーザー向けメッセージ、なければ null を返す。 */
export function validateImageFile(file: File | null): string | null {
  if (!file) return "画像を選んでください。";
  if (!ALLOWED.includes((file.type || "").toLowerCase())) {
    return "対応していない形式です（JPEG / PNG / HEIC）。";
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return "画像が大きすぎます（10MBまで）。";
  }
  return null;
}

/** File を data URL（プレビュー/保存用）に変換する。 */
export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
