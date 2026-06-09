import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Drawer } from "./Drawer";

describe("Drawer（ハンバーガーのドロワー）", () => {
  it("閉じているときは中身を描画しないことを検証する", () => {
    render(
      <Drawer open={false} onClose={() => {}} title="メニュー">
        <button type="button">アカウント</button>
      </Drawer>,
    );
    expect(screen.queryByText("アカウント")).not.toBeInTheDocument();
  });

  it("開いているとき dialog として中身を描画することを検証する", () => {
    render(
      <Drawer open onClose={() => {}} title="メニュー">
        <button type="button">アカウント</button>
      </Drawer>,
    );
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("アカウント")).toBeInTheDocument();
  });

  it("Esc キーで onClose が呼ばれることを検証する", () => {
    const onClose = vi.fn();
    render(
      <Drawer open onClose={onClose} title="メニュー">
        <span>x</span>
      </Drawer>,
    );
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("スクリム（背景）クリックで onClose が呼ばれることを検証する", () => {
    const onClose = vi.fn();
    render(
      <Drawer open onClose={onClose} title="メニュー">
        <span>x</span>
      </Drawer>,
    );
    fireEvent.click(screen.getByTestId("drawer-scrim"));
    expect(onClose).toHaveBeenCalled();
  });

  it("閉じるボタンで onClose が呼ばれることを検証する", () => {
    const onClose = vi.fn();
    render(
      <Drawer open onClose={onClose} title="メニュー">
        <span>x</span>
      </Drawer>,
    );
    fireEvent.click(screen.getByRole("button", { name: "閉じる" }));
    expect(onClose).toHaveBeenCalled();
  });
});
