// 弔事/慶事トーン分類（BR-4-TONE）。弔事は静かな配色・コピーに。

const MOURNING = ["香典", "御霊前", "御仏前", "法事", "法要", "弔慰", "お悔やみ"];

export type Tone = "mourning" | "celebration";

export function toneOf(purpose: string): Tone {
  const p = purpose || "";
  return MOURNING.some((k) => p.includes(k)) ? "mourning" : "celebration";
}
