import { describe, expect, test } from "vitest";
import type { Household, Member } from "../types";
import { isSharing, memberDisplay } from "./household";

const m = (over: Partial<Member>): Member => ({
  user_id: "u-1",
  role: "member",
  email: "",
  ...over,
});

const household = (memberCount: number): Household => ({
  id: "h-1",
  name: "わが家",
  invite_code: "ABCDEF",
  members: Array.from({ length: memberCount }, (_, i) => ({
    user_id: `u-${i}`,
    role: i === 0 ? "owner" : "member",
    email: "",
  })),
});

describe("memberDisplay", () => {
  test("自分はメールの有無に関わらず「あなた」と表示する", () => {
    const me = "me-123";
    expect(memberDisplay(m({ user_id: me, email: "" }), me).name).toBe("あなた");
    expect(memberDisplay(m({ user_id: me, email: "me@example.com" }), me).name).toBe("あなた");
  });

  test("他メンバーはメールがあればメールを表示する", () => {
    expect(memberDisplay(m({ user_id: "u-9", email: "a@example.com" }), "me-123").name).toBe(
      "a@example.com",
    );
  });

  test("他メンバーでメール不明でも UUID は出さず汎用ラベルにする", () => {
    const d = memberDisplay(
      m({ user_id: "97442ad8-5061-70a0-ca7f-52bd9a90b4ad", email: "" }),
      "me-123",
    );
    expect(d.name).toBe("ご家族のメンバー");
    expect(d.name).not.toContain("97442ad8");
  });

  test("owner 判定と自分判定を返す", () => {
    const me = "me-123";
    expect(memberDisplay(m({ user_id: me, role: "owner" }), me)).toMatchObject({
      isOwner: true,
      isMe: true,
    });
    expect(memberDisplay(m({ user_id: "u-9", role: "member" }), me)).toMatchObject({
      isOwner: false,
      isMe: false,
    });
  });
});

describe("isSharing", () => {
  test("メンバーが自分だけ（1人）なら共有していない", () => {
    expect(isSharing(household(1))).toBe(false);
  });

  test("メンバーが2人以上なら共有している", () => {
    expect(isSharing(household(2))).toBe(true);
    expect(isSharing(household(3))).toBe(true);
  });
});
