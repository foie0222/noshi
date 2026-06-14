import { Browser } from "@capacitor/browser";
import { Capacitor } from "@capacitor/core";

/**
 * 外部 URL（楽天アフィリエイト等）を開く（#230/#195）。
 *
 * iOS ネイティブは SFSafariViewController（@capacitor/browser）で開く。理由:
 *  - 埋め込み WebView 内の target="_blank" は遷移に失敗しがちで、お返し提案の購入導線が死ぬ。
 *  - アフィリエイト計測（hb.afl.rakuten.co.jp の redirect）は実 Safari エンジンで確実に通る。
 *
 * Web では何もせず false を返し、既定の <a target="_blank"> の動作に委ねる。
 *
 * @returns ネイティブで開いた（＝呼び出し側で既定の <a> 遷移を preventDefault すべき）なら true。
 */
export function openExternalUrl(url: string): boolean {
  if (!url) return false;
  if (Capacitor.isNativePlatform()) {
    void Browser.open({ url });
    return true;
  }
  return false;
}
