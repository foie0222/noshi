// 外部サイト（お返し品のアフィリエイトリンク）を開く。
//
// ネイティブでは必ずシステムのブラウザ（SFSafariViewController）で開く。
// アプリ内 WebView に楽天を読み込ませると、戻る手段が無くアプリから出られなくなり、
// 「アプリ内で任意の Web を閲覧できる」状態にもなってしまうため。

import { Browser } from "@capacitor/browser";

import { isNativePlatform } from "./platform";

/** 開いてよいのは https のみ。javascript: や data: を実行させない。 */
function isSafe(url: string): boolean {
  try {
    return new URL(url).protocol === "https:";
  } catch {
    return false;
  }
}

export async function openExternal(url: string): Promise<void> {
  if (!isSafe(url)) return;
  if (!isNativePlatform()) {
    window.open(url, "_blank", "noopener,noreferrer");
    return;
  }
  // 開けなかっただけで画面を壊さない（リンク以外の操作は続けられる）
  await Browser.open({ url }).catch(() => {});
}
