// 許可オリジン（#72/#103/#105/#194）。API Gateway・FastAPI・画像 S3 の CORS で共用する。
// - noshi.me: 本番フロント
// - cloudfront: 旧ドメイン移行期の併用
// - https://localhost: iOS（Capacitor 内包）WebView のオリジン（iosScheme=https）。
//   画像の署名付き POST/GET もアプリ内から行うため S3 CORS でも必須。
export const ALLOWED_ORIGINS = [
  "https://noshi.me",
  "https://d1u0sgslky88ja.cloudfront.net",
  "https://localhost",
] as const;
