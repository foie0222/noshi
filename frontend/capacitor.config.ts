import type { CapacitorConfig } from "@capacitor/cli";

// Capacitor 設定（#193）。既存 React(Vite) 資産を内包し iOS アプリ化する。
// webDir は Vite のビルド成果物。appId は #210 で登録する App ID と一致させる。
const config: CapacitorConfig = {
  appId: "me.noshi.app",
  appName: "noshi",
  webDir: "dist",
  ios: {
    // 本番は dist 同梱で動かす。dev のホットリロードは server.url を一時的に使う想定（本番では設定しない）。
    contentInset: "always",
  },
};

export default config;
