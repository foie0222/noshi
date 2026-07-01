// Amazon Cognito（User Pool）への最小ログイン。素の fetch で USER_PASSWORD_AUTH。
// IdToken を localStorage に保持して API に Bearer 送信する。
// ソーシャルは Web は Hosted UI へリダイレクト、iOS ネイティブは SFSafariViewController
// （@capacitor/browser）で開き、カスタムスキームのコールバックを appUrlOpen で受ける（#204）。

import { App as CapApp } from "@capacitor/app";
import { Browser } from "@capacitor/browser";
import { decodeJwtPayload, isExpired } from "./jwt";
import { isNativePlatform } from "./platform";

// iOS ネイティブのソーシャル用カスタムスキーム（Info.plist の CFBundleURLTypes と一致）。
const NATIVE_OAUTH_REDIRECT = "me.noshi.app://callback";
/** OAuth の redirect_uri。authorize と token 交換で必ず同一値を使う（テスト対象）。 */
export function oauthRedirectUri(): string {
  return isNativePlatform() ? NATIVE_OAUTH_REDIRECT : `${location.origin}/`;
}

const REGION = import.meta.env.VITE_AWS_REGION ?? "ap-northeast-1";
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID ?? "";
const ENDPOINT = `https://cognito-idp.${REGION}.amazonaws.com/`;
const TOKEN_KEY = "noshi-id-token";
const DOMAIN = (import.meta.env.VITE_COGNITO_DOMAIN ?? "").replace(/\/$/, "");
// 一時保存キー。iOS Safari はクロスサイトのログイン往復で sessionStorage を保持しない
// ことがあるため localStorage を使い、callback 処理後（cleanup）に確実に削除する。
const VERIFIER_KEY = "noshi_pkce_verifier";
const STATE_KEY = "noshi_oauth_state";
const PROVIDER_KEY = "noshi_oauth_provider";
const RETRY_KEY = "noshi_oauth_retry";

// Cognito 側の IdP 名と同一文字列にする。Apple は Cognito の予約プロバイダ名
// "SignInWithApple"（authorize の identity_provider に渡す値）。
export type SocialProvider = "Google" | "LINE" | "SignInWithApple";

export function authEnabled(): boolean {
  return CLIENT_ID.length > 0;
}

/** ソーシャルログインが使えるか（Cognito ドメイン未注入のローカルではボタン非表示）。 */
export function socialEnabled(): boolean {
  return authEnabled() && DOMAIN.length > 0;
}

export function getIdToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}
export function isLoggedIn(): boolean {
  const t = getIdToken();
  return !!t && !isExpired(t);
}
export function currentEmail(): string {
  return decodeJwtPayload(getIdToken())?.email || "";
}
export function signOut(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * リロード時の初期画面を決める。認証が有効で未ログインのときだけログイン画面、
 * それ以外（ログイン済み or 認証無効）はホームを復元する。
 * これがないと localStorage にトークンがあっても毎回ログイン画面に戻ってしまう。
 */
export function pickInitialScreen(authOn: boolean, loggedIn: boolean): "home" | "login" {
  return authOn && !loggedIn ? "login" : "home";
}

/** Cognito のエラー型を分かりやすい日本語にする。 */
export function cognitoErrorMessage(type: string, fallback = "エラーが発生しました。"): string {
  const t = type || "";
  if (t.includes("UsernameExistsException")) return "そのメールアドレスは既に登録されています。";
  if (t.includes("UserNotConfirmedException"))
    return "メール確認が未完了です。確認コードを入力してください。";
  if (t.includes("CodeMismatchException")) return "確認コードが違います。";
  if (t.includes("ExpiredCodeException"))
    return "確認コードの有効期限が切れました。再送してください。";
  if (t.includes("InvalidPasswordException"))
    return "パスワードは8文字以上で、英小文字と数字を含めてください。";
  if (t.includes("LimitExceededException"))
    return "試行回数が上限に達しました。しばらく待ってからお試しください。";
  if (t.includes("NotAuthorizedException") || t.includes("UserNotFoundException"))
    return "メールアドレスかパスワードが違います。";
  return fallback;
}

interface CognitoResponse {
  AuthenticationResult?: { IdToken?: string };
  __type?: string;
  message?: string;
}

async function call(target: string, body: object): Promise<CognitoResponse> {
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  });
  const data: CognitoResponse = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(cognitoErrorMessage(data.__type || "", data.message));
  return data;
}

export async function signUp(email: string, password: string): Promise<void> {
  await call("SignUp", {
    ClientId: CLIENT_ID,
    Username: email,
    Password: password,
    UserAttributes: [{ Name: "email", Value: email }],
  });
}
export async function confirmSignUp(email: string, code: string): Promise<void> {
  await call("ConfirmSignUp", { ClientId: CLIENT_ID, Username: email, ConfirmationCode: code });
}
/** パスワード再設定: 確認コードを登録メールへ送る。 */
export async function forgotPassword(email: string): Promise<void> {
  await call("ForgotPassword", { ClientId: CLIENT_ID, Username: email });
}
/** パスワード再設定: 確認コードと新パスワードで確定する。 */
export async function confirmForgotPassword(
  email: string,
  code: string,
  newPassword: string,
): Promise<void> {
  await call("ConfirmForgotPassword", {
    ClientId: CLIENT_ID,
    Username: email,
    ConfirmationCode: code,
    Password: newPassword,
  });
}

export async function signIn(email: string, password: string): Promise<void> {
  const data = await call("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: CLIENT_ID,
    AuthParameters: { USERNAME: email, PASSWORD: password },
  });
  const idToken = data?.AuthenticationResult?.IdToken;
  if (!idToken) throw new Error("ログインに失敗しました。");
  localStorage.setItem(TOKEN_KEY, idToken);
}

// ---- ソーシャルログイン（認可コード + PKCE・依存ゼロ）。スペック§5 ----

/** バイト列を base64url（パディングなし）に。 */
export function b64url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/** PKCE の verifier と challenge（S256）を生成する。 */
export async function pkcePair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return { verifier, challenge: b64url(new Uint8Array(digest)) };
}

export function buildAuthorizeUrl(p: {
  domain: string;
  clientId: string;
  provider: SocialProvider;
  redirectUri: string;
  state: string;
  challenge: string;
}): string {
  const q = new URLSearchParams({
    identity_provider: p.provider,
    response_type: "code",
    client_id: p.clientId,
    redirect_uri: p.redirectUri,
    scope: "openid email profile",
    state: p.state,
    code_challenge: p.challenge,
    code_challenge_method: "S256",
  });
  return `${p.domain}/oauth2/authorize?${q.toString()}`;
}

/** Google/LINE の認証画面を開く。Web はリダイレクト、iOS ネイティブは SFSafariViewController。 */
export async function socialSignIn(provider: SocialProvider): Promise<void> {
  const { verifier, challenge } = await pkcePair();
  const state = b64url(crypto.getRandomValues(new Uint8Array(16)));
  localStorage.setItem(VERIFIER_KEY, verifier);
  localStorage.setItem(STATE_KEY, state);
  localStorage.setItem(PROVIDER_KEY, provider);
  const url = buildAuthorizeUrl({
    domain: DOMAIN,
    clientId: CLIENT_ID,
    provider,
    redirectUri: oauthRedirectUri(),
    state,
    challenge,
  });
  if (isNativePlatform()) {
    // 埋め込み WebView だと Google が拒否するため、ネイティブの安全ブラウザで開く。
    // 戻りは me.noshi.app://callback → registerNativeAuthCallback が処理する。
    await Browser.open({ url });
  } else {
    location.href = url;
  }
}

export type CallbackResult = "ok" | "retry" | "error" | "none";

type CallbackClass =
  | { kind: "none" }
  | { kind: "retry"; provider: SocialProvider }
  | { kind: "token"; code: string }
  | { kind: "error" };

/** コールバック URL の分岐判定（純関数・テスト対象）。 */
export function classifyCallback(
  params: URLSearchParams,
  stored: { state: string | null; provider: SocialProvider | null; retried: boolean },
): CallbackClass {
  const code = params.get("code");
  const error = params.get("error");
  if (!code && !error) return { kind: "none" };
  if (error) {
    const desc = params.get("error_description") ?? "";
    // Pre-signup の自動統合直後だけ1回リトライ（スペック§4/§5）。provider は保存値のみ信用
    if (desc.includes("ALREADY_LINKED_RETRY") && !stored.retried && stored.provider) {
      return { kind: "retry", provider: stored.provider };
    }
    return { kind: "error" };
  }
  if (!code) return { kind: "error" };
  const state = params.get("state");
  if (!state || !stored.state || state !== stored.state) return { kind: "error" }; // CSRF対策
  return { kind: "token", code };
}

// StrictMode の二重マウントやリロード後の再入で、使用済み code を再交換して
// 誤った "error" にならないよう、実処理に入るのは1回だけに制限する。
let callbackHandled = false;

/** code/error を含む URL パラメータを処理して結果を返す（Web/native 共通・スペック§5）。 */
async function processCallback(params: URLSearchParams): Promise<CallbackResult> {
  const v = localStorage.getItem(PROVIDER_KEY);
  const sp = v === "Google" || v === "LINE" || v === "SignInWithApple" ? v : null;
  const cls = classifyCallback(params, {
    state: localStorage.getItem(STATE_KEY),
    provider: sp,
    retried: localStorage.getItem(RETRY_KEY) === "1",
  });
  if (cls.kind === "none") return "none";
  if (callbackHandled) return "none"; // StrictMode の二重実行・再入を防ぐ
  callbackHandled = true;

  const stripUrl = () => history.replaceState(null, "", location.pathname);
  const cleanup = () => {
    for (const k of [VERIFIER_KEY, STATE_KEY, PROVIDER_KEY, RETRY_KEY]) localStorage.removeItem(k);
    stripUrl();
  };

  if (cls.kind === "retry") {
    localStorage.setItem(RETRY_KEY, "1");
    await socialSignIn(cls.provider); // 新しい verifier/state で再認可（RETRY_KEY は残す）
    return "retry";
  }
  if (cls.kind === "error") {
    cleanup();
    return "error";
  }

  const verifier = localStorage.getItem(VERIFIER_KEY) ?? "";
  if (!verifier) {
    cleanup();
    return "error";
  }
  try {
    const res = await fetch(`${DOMAIN}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: CLIENT_ID,
        code: cls.code,
        redirect_uri: oauthRedirectUri(),
        code_verifier: verifier, // PKCE: verifier 無しの交換経路は作らない（スペック§3）
      }),
    });
    const data = (await res.json().catch(() => ({}))) as { id_token?: string };
    if (!res.ok || !data.id_token) {
      cleanup();
      return "error";
    }
    localStorage.setItem(TOKEN_KEY, data.id_token);
    cleanup();
    return "ok";
  } catch {
    cleanup();
    return "error";
  }
}

/** アプリ起動時に1回呼ぶ（Web）。現在 URL の code/error を処理する。 */
export async function handleAuthCallback(): Promise<CallbackResult> {
  return processCallback(new URLSearchParams(location.search));
}

/**
 * iOS ネイティブのソーシャル コールバックを購読する（#204）。
 * me.noshi.app://callback?code=... で復帰した際に code を交換し、結果を onResult に渡す。
 * Web では何もしない。
 */
export function registerNativeAuthCallback(onResult: (r: CallbackResult) => void): () => void {
  if (!isNativePlatform()) return () => {};
  const handle = CapApp.addListener("appUrlOpen", async ({ url }) => {
    let params: URLSearchParams;
    try {
      params = new URLSearchParams(new URL(url).search);
    } catch {
      return;
    }
    if (!params.has("code") && !params.has("error")) return;
    callbackHandled = false; // ネイティブの新規コールバックは毎回処理する
    const r = await processCallback(params);
    await Browser.close().catch(() => {});
    onResult(r);
  });
  // 二重登録の保険として購読解除を返す（呼び出し側が useEffect の cleanup で使う）。
  return () => {
    void handle.then((h) => h.remove());
  };
}
