import type { CapacitorConfig } from "@capacitor/cli";

// Capacitor 設定（#193）。既存 React(Vite) 資産を内包し iOS アプリ化する。
// webDir は Vite のビルド成果物。appId は #210 で登録する App ID と一致させる。
const config: CapacitorConfig = {
  appId: "me.noshi.app",
  appName: "noshi",
  webDir: "dist",
  server: {
    // iOS WebView のスキームを https にし、オリジンを https://localhost にする（#194）。
    // 既定の capacitor:// は API Gateway の CORS が「不正な形式」として弾くため。
    // Android 既定(https)とも揃い、クッキー/ストレージ面でも推奨構成。
    iosScheme: "https",
  },
  plugins: {
    // API 通信を WebView の fetch ではなくネイティブ URLSession 経由にする（#194）。
    // WKWebView の fetch が 200 応答でも "Load failed" で reject する不調を根本回避し、
    // CORS もネイティブ通信では対象外になる。Web ビルドでは無影響（ネイティブ時のみ patch）。
    CapacitorHttp: { enabled: true },
  },
  ios: {
    // 本番は dist 同梱で動かす。dev のホットリロードは server.url を一時的に使う想定（本番では設定しない）。
    contentInset: "always",
  },
};

export default config;
