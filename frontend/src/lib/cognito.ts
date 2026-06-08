// Amazon Cognito（User Pool）への最小ログイン。依存追加なし（素の fetch）。
// USER_PASSWORD_AUTH を使い、IdToken を localStorage に保持して API に Bearer 送信する。

import { decodeJwtPayload, isExpired } from "./jwt";

const REGION = import.meta.env.VITE_AWS_REGION ?? "ap-northeast-1";
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID ?? "";
const ENDPOINT = `https://cognito-idp.${REGION}.amazonaws.com/`;
const TOKEN_KEY = "noshi-id-token";

export function authEnabled(): boolean {
  return CLIENT_ID.length > 0;
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

/** Cognito のエラー型を分かりやすい日本語にする。 */
export function cognitoErrorMessage(type: string, fallback = "エラーが発生しました。"): string {
  const t = type || "";
  if (t.includes("UsernameExistsException")) return "そのメールアドレスは既に登録されています。";
  if (t.includes("UserNotConfirmedException")) return "メール確認が未完了です。確認コードを入力してください。";
  if (t.includes("CodeMismatchException")) return "確認コードが違います。";
  if (t.includes("ExpiredCodeException")) return "確認コードの有効期限が切れました。再送してください。";
  if (t.includes("InvalidPasswordException")) return "パスワードは8文字以上で、英小文字と数字を含めてください。";
  if (t.includes("LimitExceededException")) return "試行回数が上限に達しました。しばらく待ってからお試しください。";
  if (t.includes("NotAuthorizedException") || t.includes("UserNotFoundException"))
    return "メールアドレスかパスワードが違います。";
  return fallback;
}

async function call(target: string, body: object): Promise<any> {
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(cognitoErrorMessage(data.__type || "", data.message));
  return data;
}

export async function signUp(email: string, password: string): Promise<void> {
  await call("SignUp", {
    ClientId: CLIENT_ID, Username: email, Password: password,
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
export async function confirmForgotPassword(email: string, code: string, newPassword: string): Promise<void> {
  await call("ConfirmForgotPassword", {
    ClientId: CLIENT_ID, Username: email, ConfirmationCode: code, Password: newPassword,
  });
}

export async function signIn(email: string, password: string): Promise<void> {
  const data = await call("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH", ClientId: CLIENT_ID,
    AuthParameters: { USERNAME: email, PASSWORD: password },
  });
  const idToken = data?.AuthenticationResult?.IdToken;
  if (!idToken) throw new Error("ログインに失敗しました。");
  localStorage.setItem(TOKEN_KEY, idToken);
}
