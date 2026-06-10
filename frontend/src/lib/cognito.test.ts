import { describe, expect, it } from "vitest";
import { cognitoErrorMessage, pickInitialScreen } from "./cognito";

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
