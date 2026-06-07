import { describe, it, expect } from "vitest";
import { otoshidamaRange } from "./otoshidama";

describe("お年玉の年齢別相場", () => {
  it("未就学児(0-6歳)は0〜1,000円が目安であることを検証する", () => {
    const r = otoshidamaRange(5);
    expect(r.low).toBe(0);
    expect(r.high).toBe(1000);
    expect(r.bracket).toContain("未就学");
  });
  it("小学校低学年(7-9歳)は1,000〜3,000円であることを検証する", () => {
    const r = otoshidamaRange(8);
    expect(r.low).toBe(1000);
    expect(r.high).toBe(3000);
  });
  it("小学校高学年(10-12歳)は3,000〜5,000円であることを検証する", () => {
    expect(otoshidamaRange(11)).toMatchObject({ low: 3000, high: 5000 });
  });
  it("中学生(13-15歳)は5,000円であることを検証する", () => {
    expect(otoshidamaRange(14)).toMatchObject({ low: 5000, high: 5000 });
  });
  it("高校生(16-18歳)は5,000〜10,000円であることを検証する", () => {
    expect(otoshidamaRange(17)).toMatchObject({ low: 5000, high: 10000 });
  });
  it("大学生以上(19歳〜)は10,000円であることを検証する", () => {
    expect(otoshidamaRange(20)).toMatchObject({ low: 10000, high: 10000 });
  });
  it("各区分は目安の一言(note)を持つことを検証する", () => {
    expect(otoshidamaRange(8).note.length).toBeGreaterThan(0);
  });
});
