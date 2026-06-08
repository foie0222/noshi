import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Logo } from "./Logo";

describe("Logo（のし ブランドマーク）", () => {
  it("full は 朱赤の印「の」＋ 文字「し」で、続けて「のし」と読めることを検証する", () => {
    const { container } = render(<Logo variant="full" />);
    // 印「の」と 文字「し」の2要素
    expect(container.textContent).toBe("のし");
    const seal = container.querySelector("[data-part='seal']");
    const word = container.querySelector("[data-part='word']");
    expect(seal?.textContent).toBe("の");
    expect(word?.textContent).toBe("し");
  });

  it("mark は 印「の」のみで 文字を出さないことを検証する", () => {
    const { container } = render(<Logo variant="mark" />);
    expect(container.textContent).toBe("の");
    expect(container.querySelector("[data-part='word']")).toBeNull();
  });

  it("word は 印なしで「のし」を綴ることを検証する（単体可読性のため）", () => {
    const { container } = render(<Logo variant="word" />);
    expect(container.textContent).toBe("のし");
    expect(container.querySelector("[data-part='seal']")).toBeNull();
  });
});
