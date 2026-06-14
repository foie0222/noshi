import { Browser } from "@capacitor/browser";
import { Capacitor } from "@capacitor/core";

/**
 * 外部 URL（楽天アフィリエイト等）を開く（#230/#195）。
 *
 * ネイティブ（iOS=SFSafariViewController / Android=Chrome Custom Tabs）は @capacitor/browser で開く。理由:
 *  - 埋め込み WebView 内の target="_blank" は遷移に失敗しがちで、お返し提案の購入導線が死ぬ。
 *  - アフィリエイト計測（hb.afl.rakuten.co.jp の redirect）は実ブラウザエンジンで確実に通る。
 *
 * Web では何もせず false を返し、既定の <a target="_blank"> の動作に委ねる。
 *
 * @returns ネイティブで開いた（＝呼び出し側で既定の <a> 遷移を preventDefault すべき）なら true。
 */
export function openExternalUrl(url: string): boolean {
  if (!url) return false;
  if (Capacitor.isNativePlatform()) {
    // 失敗時は最低限 window.open で再試行し、preventDefault 済みでも遷移不能にならないようにする。
    Browser.open({ url }).catch(() => {
      window.open(url, "_blank");
    });
    return true;
  }
  return false;
}
