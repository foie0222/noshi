// 季節ナッジ判定（BR-5-SEASON）。年始は12月のお歳暮と重なるため優先。

export type Season = "ochugen" | "oseibo" | "newyear" | "none";

export function seasonOf(month: number): Season {
  if (month === 12 || month === 1) return "newyear"; // 年始優先
  if (month === 11) return "oseibo";
  if (month >= 6 && month <= 8) return "ochugen";
  return "none";
}

export function seasonNudge(season: Season): string {
  switch (season) {
    case "ochugen":
      return "お中元の季節です。日頃の感謝を、贈りませんか。";
    case "oseibo":
      return "お歳暮の季節です。一年のお礼を伝えましょう。";
    case "newyear":
      return "年始のご挨拶の季節です。";
    default:
      return "";
  }
}
