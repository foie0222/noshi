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

/**
 * data URL の画像を長辺 maxDim 以内へ縮小し JPEG Blob にする（#35）。
 * 実写真は数MBあるため、アップロード前にここで小さくする。
 */
export function downscaleImage(dataUrl: string, maxDim = 1280, quality = 0.82): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
      const w = Math.round(img.width * scale);
      const h = Math.round(img.height * scale);
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("画像を処理できませんでした。"));
        return;
      }
      ctx.drawImage(img, 0, 0, w, h);
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error("画像を変換できませんでした。"))),
        "image/jpeg",
        quality,
      );
    };
    img.onerror = () => reject(new Error("画像を読み込めませんでした。"));
    img.src = dataUrl;
  });
}
