// JWT（Cognito IdToken）の最小デコード。署名検証はサーバ側が行う。
// ここでは表示（email）と期限切れ判定のために payload を読むだけ。

export interface JwtPayload {
  sub?: string;
  email?: string;
  exp?: number;
  [k: string]: unknown;
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  const parts = (token || "").split(".");
  if (parts.length < 2) return null;
  try {
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    return JSON.parse(decodeURIComponent(escape(atob(padded))));
  } catch {
    return null;
  }
}

export function isExpired(token: string, nowSec: number = Math.floor(Date.now() / 1000)): boolean {
  const p = decodeJwtPayload(token);
  if (!p || typeof p.exp !== "number") return true;
  return p.exp <= nowSec;
}
