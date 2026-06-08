import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Icon } from "./Icon";

describe("Icon（ラインアイコン）", () => {
  it("既知の name で 24x24 viewBox の svg を currentColor stroke で描画することを検証する", () => {
    const { container } = render(<Icon name="home" />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute("viewBox")).toBe("0 0 24 24");
    expect(svg?.getAttribute("stroke")).toBe("currentColor");
    expect(svg?.getAttribute("fill")).toBe("none");
    // home グリフのパスが描画されている
    expect(svg?.innerHTML).toContain("path");
  });

  it("size 指定が width/height に反映されることを検証する", () => {
    const { container } = render(<Icon name="lock" size={18} />);
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("width")).toBe("18");
    expect(svg?.getAttribute("height")).toBe("18");
  });

  it("未知の name では空（パスなし）の svg を描画することを検証する", () => {
    const { container } = render(<Icon name={"__nope__" as never} />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg?.innerHTML).toBe("");
  });
});
