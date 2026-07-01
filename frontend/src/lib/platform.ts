// 実行プラットフォーム判定の共有ユーティリティ。
// Capacitor.isNativePlatform() のラッパーが各所に散らないよう、ここに一本化する。

import { Capacitor } from "@capacitor/core";

/** ネイティブ（iOS/Android アプリ）上で動作しているか。Web ブラウザでは false。 */
export function isNativePlatform(): boolean {
  return Capacitor.isNativePlatform();
}
