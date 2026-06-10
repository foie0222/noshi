import type { Household, Member } from "../types";

export interface MemberDisplay {
  /** 画面に出す人間可読のラベル。UUID は決して露出させない。 */
  name: string;
  isOwner: boolean;
  isMe: boolean;
}

/**
 * 共有メンバーの表示情報を組み立てる。
 * 自分は「あなた」、他人はメール、メール不明でも UUID ではなく汎用ラベルにする(#79)。
 */
export function memberDisplay(member: Member, meId: string): MemberDisplay {
  const isMe = member.user_id === meId;
  const name = isMe ? "あなた" : member.email || "ご家族のメンバー";
  return { name, isOwner: member.role === "owner", isMe };
}

/**
 * すでに家族と台帳を共有しているか（自分以外のメンバーがいるか）。
 * 共有状況に応じて「参加」導線などの出し分けに使う(#80)。
 */
export function isSharing(household: Household): boolean {
  return household.members.length > 1;
}
