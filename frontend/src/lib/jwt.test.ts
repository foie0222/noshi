import { describe, it, expect } from "vitest";
import { decodeJwtPayload, isExpired } from "./jwt";

// テスト用に署名なしの JWT を組み立てる（payload だけ読めれば良い）。
function makeJwt(payload: object): string {
  const b64 = (o: object) =>
    btoa(JSON.stringify(o)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${b64({ alg: "none" })}.${b64(payload)}.sig`;
}

describe("JWT ペイロードのデコード", () => {
  it("sub と email を取り出せることを検証する", () => {
    const p = decodeJwtPayload(makeJwt({ sub: "user-1", email: "taro@example.jp", exp: 9999999999 }));
    expect(p?.sub).toBe("user-1");
    expect(p?.email).toBe("taro@example.jp");
  });

  it("壊れたトークンは null を返すことを検証する", () => {
    expect(decodeJwtPayload("not-a-jwt")).toBeNull();
  });
});

describe("JWT の有効期限判定", () => {
  it("exp が過去なら期限切れと判定することを検証する", () => {
    const tok = makeJwt({ sub: "u", exp: 1000 });
    expect(isExpired(tok, 2000)).toBe(true);
  });

  it("exp が未来なら有効と判定することを検証する", () => {
    const tok = makeJwt({ sub: "u", exp: 5000 });
    expect(isExpired(tok, 2000)).toBe(false);
  });

  it("exp が無い/壊れたトークンは期限切れ扱いにすることを検証する", () => {
    expect(isExpired("broken", 2000)).toBe(true);
  });
});
