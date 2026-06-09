// お年玉の年齢別相場（BR-7-OTOSHIDAMA）。一般的な目安・データ非依存。

export interface OtoshidamaRange {
  low: number;
  high: number;
  bracket: string;
  note: string;
}

/** お子さんの年齢入力が有効か（0〜25の整数のみ）（#52）。 */
export function isValidChildAge(input: string): boolean {
  const s = (input ?? "").trim();
  if (!/^\d+$/.test(s)) return false; // 整数のみ（負数・小数・非数値・空を弾く）
  const n = Number(s);
  return n >= 0 && n <= 25;
}

export function otoshidamaRange(age: number): OtoshidamaRange {
  if (age <= 6)
    return {
      low: 0,
      high: 1000,
      bracket: "未就学児",
      note: "現金より図書カードやおもちゃでも喜ばれます。",
    };
  if (age <= 9)
    return { low: 1000, high: 3000, bracket: "小学校低学年", note: "1,000〜3,000円が目安です。" };
  if (age <= 12)
    return { low: 3000, high: 5000, bracket: "小学校高学年", note: "3,000〜5,000円が目安です。" };
  if (age <= 15) return { low: 5000, high: 5000, bracket: "中学生", note: "5,000円が目安です。" };
  if (age <= 18)
    return { low: 5000, high: 10000, bracket: "高校生", note: "5,000〜10,000円が目安です。" };
  return { low: 10000, high: 10000, bracket: "大学生以上", note: "10,000円が目安です。" };
}
