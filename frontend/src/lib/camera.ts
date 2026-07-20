// ネイティブカメラ撮影（#203 / 4.2 対策 #197）。
// iOS/Android では @capacitor/camera でネイティブ撮影・ライブラリ選択を行い、
// 得た画像を既存の onPickImage（検証→ダウンスケール→抽出）パスへ File として合流させる。
// Web では本モジュールを使わず、従来の <input type="file"> 経路に委ねる。

import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";

/** 撮影ソース。UI 側の自前チューザー（#402）で選ばせ、OS のアクションシートは使わない。 */
export type CaptureSource = "camera" | "photos";

/** カメラ・写真ライブラリの両方が拒否され、撮影に進めない状態。UI は設定誘導を出す。 */
export class CameraPermissionDeniedError extends Error {
  constructor() {
    super("カメラ・写真へのアクセスが許可されていません。");
    this.name = "CameraPermissionDeniedError";
  }
}

function looksLikeCancel(message: string): boolean {
  return /cancel/i.test(message);
}

function looksLikePermissionError(message: string): boolean {
  return /denied|permission|not authorized|authoriz/i.test(message);
}

/**
 * ネイティブのカメラ/フォトライブラリで1枚撮影（選択）し File を返す。
 * - キャンセル時は null（呼び出し側はエラー表示せず握る）。
 * - カメラ・写真の両権限が denied のとき、または撮影が権限エラーで失敗したときは
 *   CameraPermissionDeniedError を投げる（UI がフォールバックと設定誘導を出す）。
 *
 * 返す File は既存 onPickImage の検証（形式/サイズ）とダウンスケールにそのまま通る。
 */
export async function captureNativePhoto(source: CaptureSource): Promise<File | null> {
  // 選んだソースの権限が拒否済みなら OS ダイアログは出ないため、早期に設定誘導へ倒す。
  const perm = await Camera.checkPermissions();
  if (source === "camera" ? perm.camera === "denied" : perm.photos === "denied") {
    throw new CameraPermissionDeniedError();
  }

  let photo: Awaited<ReturnType<typeof Camera.getPhoto>>;
  try {
    photo = await Camera.getPhoto({
      // OS のアクションシート（CameraSource.Prompt）は iPad で popover 起点を解決できず
      // 即例外になり審査却下の原因となった（#402 / Guideline 2.1(a)）。ソースは自前 UI で
      // 選ばせ、ここでは Camera / Photos を直接指定する（どちらも全画面提示で iPad 安全）。
      source: source === "camera" ? CameraSource.Camera : CameraSource.Photos,
      presentationStyle: "fullscreen", // iPad でも popover に依存しない
      resultType: CameraResultType.Uri, // 巨大 Base64 をブリッジに通さずメモリを節約。fetch で blob 化する。
      quality: 80,
      width: 2048, // 長辺の上限。通信量・抽出コストを抑える（Web のダウンスケール仕様と整合）。
      correctOrientation: true, // EXIF Orientation を適用し、回転ズレによる抽出精度低下を防ぐ。
    });
  } catch (e) {
    const message = String((e as Error)?.message ?? e);
    if (looksLikeCancel(message)) return null;
    if (looksLikePermissionError(message)) throw new CameraPermissionDeniedError();
    throw e;
  }

  if (!photo.webPath) return null;
  const blob = await (await fetch(photo.webPath)).blob();
  const format = photo.format || "jpeg";
  const type = blob.type || `image/${format}`;
  return new File([blob], `capture.${format === "jpeg" ? "jpg" : format}`, { type });
}
