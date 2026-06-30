// 認証トークン（Cognito IdToken）の永続化（#207 / 4.2 加点 #197）。
//
// ネイティブ（iOS/Android）は Keychain（@aparajita/capacitor-secure-storage）に保管する。
// WKWebView の localStorage は端末内に平文で残りうるため、トークンは OS のセキュア領域へ。
// Keychain アクセスは非同期だが、API の Bearer 付与はリクエスト毎の同期パスなので、
// 起動時に hydrateToken() で同期キャッシュへ載せ、getToken() は同期で返す。
//
// Web は従来どおり localStorage を正本に同期アクセスする（挙動を一切変えない）。

import { SecureStorage } from "@aparajita/capacitor-secure-storage";
import { Capacitor } from "@capacitor/core";

const TOKEN_KEY = "noshi-id-token";

// ネイティブの同期アクセス用キャッシュ。Keychain（非同期）の現在値を映す。
let cache = "";

function isNative(): boolean {
  return Capacitor.isNativePlatform();
}

/**
 * 起動時にトークンを永続ストアから読み、ネイティブの同期キャッシュへ載せる。
 * Web は localStorage を直接同期参照するため何もしない。
 * Keychain が空/失敗でも空文字にフォールバックし、ログイン画面へ倒す。
 */
export async function hydrateToken(): Promise<void> {
  if (!isNative()) return;
  try {
    const v = await SecureStorage.getItem(TOKEN_KEY);
    cache = typeof v === "string" ? v : "";
  } catch {
    cache = "";
  }
}

/** 現在のトークンを同期で返す（API の Bearer 付与など、ホットパス用）。 */
export function getToken(): string {
  if (isNative()) return cache;
  return localStorage.getItem(TOKEN_KEY) || "";
}

/**
 * トークンを保存する。ネイティブは即座にキャッシュへ反映し Keychain へも書く
 * （永続化は非同期だが待たない。次回起動でも hydrateToken で復元される）。
 */
export function setToken(token: string): void {
  if (isNative()) {
    cache = token;
    void SecureStorage.setItem(TOKEN_KEY, token).catch(() => {});
    return;
  }
  localStorage.setItem(TOKEN_KEY, token);
}

/** トークンを消去する（ログアウト/削除）。キャッシュと永続ストアの両方から消す。 */
export function clearToken(): void {
  if (isNative()) {
    cache = "";
    void SecureStorage.removeItem(TOKEN_KEY).catch(() => {});
    return;
  }
  localStorage.removeItem(TOKEN_KEY);
}
