// ネイティブカメラ撮影（#203 / 4.2 対策 #197）。
// iOS/Android では @capacitor/camera でネイティブ撮影・ライブラリ選択を行い、
// 得た画像を既存の onPickImage（検証→ダウンスケール→抽出）パスへ File として合流させる。
// Web では本モジュールを使わず、従来の <input type="file"> 経路に委ねる。

import { Camera, CameraResultType, CameraSource } from "@capacitor/camera";
import { Capacitor } from "@capacitor/core";

/** カメラ・写真ライブラリの両方が拒否され、撮影に進めない状態。UI は設定誘導を出す。 */
export class CameraPermissionDeniedError extends Error {
  constructor() {
    super("カメラ・写真へのアクセスが許可されていません。");
    this.name = "CameraPermissionDeniedError";
  }
}

/** ネイティブ環境か。UI（撮影導線の出し分け）に使う。 */
export function isNativeCamera(): boolean {
  return Capacitor.isNativePlatform();
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
export async function captureNativePhoto(): Promise<File | null> {
  // 既に両方とも拒否済みなら OS ダイアログは出ないため、ここで早期に設定誘導へ倒す。
  const perm = await Camera.checkPermissions();
  if (perm.camera === "denied" && perm.photos === "denied") {
    throw new CameraPermissionDeniedError();
  }

  let photo: Awaited<ReturnType<typeof Camera.getPhoto>>;
  try {
    photo = await Camera.getPhoto({
      source: CameraSource.Prompt, // 撮影 or ライブラリをユーザーに選ばせる（撮影済み写真を選びたい場が多い）
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
