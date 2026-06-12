import { describe, expect, it } from "vitest";
import {
  b64url,
  buildAuthorizeUrl,
  classifyCallback,
  cognitoErrorMessage,
  pickInitialScreen,
  pkcePair,
} from "./cognito";

describe("リロード時の初期画面", () => {
  it("認証有効・ログイン済みならホームを復元する（リロードで戻らない）", () => {
    expect(pickInitialScreen(true, true)).toBe("home");
  });
  it("認証有効・未ログインならログイン画面にする", () => {
    expect(pickInitialScreen(true, false)).toBe("login");
  });
  it("認証無効ならログイン不要でホームにする", () => {
    expect(pickInitialScreen(false, false)).toBe("home");
  });
});

describe("Cognito エラーの日本語化", () => {
  it("既存ユーザーは分かりやすい文言になることを検証する", () => {
    expect(cognitoErrorMessage("UsernameExistsException")).toContain("既に登録");
  });
  it("認証失敗はメール/パスワード誤りの文言になることを検証する", () => {
    expect(cognitoErrorMessage("NotAuthorizedException")).toContain("パスワードが違います");
  });
  it("確認コード不一致は専用の文言になることを検証する", () => {
    expect(cognitoErrorMessage("CodeMismatchException")).toContain("確認コード");
  });
  it("試行上限超過は待機を促す文言になることを検証する", () => {
    expect(cognitoErrorMessage("LimitExceededException")).toContain("しばらく");
  });
  it("未知のエラーはフォールバック文言を返すことを検証する", () => {
    expect(cognitoErrorMessage("SomethingElse", "既定文言")).toBe("既定文言");
  });
});

describe("PKCE", () => {
  it("verifier/challenge は base64url 形式", async () => {
    const { verifier, challenge } = await pkcePair();
    expect(verifier).toMatch(/^[A-Za-z0-9_-]{43}$/); // 32バイト→43文字
    expect(challenge).toMatch(/^[A-Za-z0-9_-]{43}$/); // SHA-256 32バイト→43文字
  });
  it("毎回異なる値を生成する", async () => {
    const a = await pkcePair();
    const b = await pkcePair();
    expect(a.verifier).not.toBe(b.verifier);
  });
  it("b64url はパディングなしで+/を-_に置換する", () => {
    expect(b64url(new Uint8Array([251, 255, 190]))).toBe("-_--");
  });
});

describe("buildAuthorizeUrl", () => {
  it("必須パラメータが全部乗る", () => {
    const url = new URL(
      buildAuthorizeUrl({
        domain: "https://noshi-me.auth.ap-northeast-1.amazoncognito.com",
        clientId: "abc",
        provider: "LINE",
        redirectUri: "https://noshi.me/",
        state: "st",
        challenge: "ch",
      }),
    );
    expect(url.pathname).toBe("/oauth2/authorize");
    expect(url.searchParams.get("identity_provider")).toBe("LINE");
    expect(url.searchParams.get("response_type")).toBe("code");
    expect(url.searchParams.get("client_id")).toBe("abc");
    expect(url.searchParams.get("redirect_uri")).toBe("https://noshi.me/");
    expect(url.searchParams.get("scope")).toBe("openid email profile");
    expect(url.searchParams.get("state")).toBe("st");
    expect(url.searchParams.get("code_challenge")).toBe("ch");
    expect(url.searchParams.get("code_challenge_method")).toBe("S256");
  });
});

describe("classifyCallback（コールバック分岐の純関数）", () => {
  const stored = { state: "st", provider: "Google" as const, retried: false };

  it("codeもerrorも無ければnone", () => {
    expect(classifyCallback(new URLSearchParams(""), stored).kind).toBe("none");
  });
  it("リンク直後のエラーは未リトライならretry", () => {
    const p = new URLSearchParams(
      "error=invalid_request&error_description=PreSignUp+failed+with+error+ALREADY_LINKED_RETRY.",
    );
    const r = classifyCallback(p, stored);
    expect(r.kind).toBe("retry");
    expect(r.kind === "retry" && r.provider).toBe("Google");
  });
  it("リトライ済みならerror", () => {
    const p = new URLSearchParams("error=x&error_description=ALREADY_LINKED_RETRY");
    expect(classifyCallback(p, { ...stored, retried: true }).kind).toBe("error");
  });
  it("別のエラーはリトライしない", () => {
    const p = new URLSearchParams("error=access_denied&error_description=user+cancelled");
    expect(classifyCallback(p, stored).kind).toBe("error");
  });
  it("providerが保存されていなければリトライしない", () => {
    const p = new URLSearchParams("error=x&error_description=ALREADY_LINKED_RETRY");
    expect(classifyCallback(p, { ...stored, provider: null }).kind).toBe("error");
  });
  it("codeありでstate一致ならtoken交換へ", () => {
    const p = new URLSearchParams("code=abc&state=st");
    const r = classifyCallback(p, stored);
    expect(r.kind).toBe("token");
    expect(r.kind === "token" && r.code).toBe("abc");
  });
  it("state不一致はerror（CSRF対策）", () => {
    const p = new URLSearchParams("code=abc&state=evil");
    expect(classifyCallback(p, stored).kind).toBe("error");
  });
});
