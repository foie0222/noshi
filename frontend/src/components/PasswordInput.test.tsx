import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PasswordInput } from "./PasswordInput";

describe("PasswordInput（パスワード表示トグル）", () => {
  it("既定では伏字（type=password）であることを検証する", () => {
    render(<PasswordInput id="pw" value="secret" onChange={() => {}} />);
    expect(document.getElementById("pw")).toHaveAttribute("type", "password");
  });

  it("トグルを押すと表示（type=text）に切り替わることを検証する", () => {
    render(<PasswordInput id="pw" value="secret" onChange={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "パスワードを表示" }));
    expect(document.getElementById("pw")).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "パスワードを隠す" })).toBeInTheDocument();
  });

  it("もう一度押すと伏字に戻ることを検証する", () => {
    render(<PasswordInput id="pw" value="secret" onChange={() => {}} />);
    const toggle = () => screen.getByRole("button", { name: /パスワードを(表示|隠す)/ });
    fireEvent.click(toggle());
    fireEvent.click(toggle());
    expect(document.getElementById("pw")).toHaveAttribute("type", "password");
  });

  it("入力すると onChange が値で呼ばれることを検証する", () => {
    const onChange = vi.fn();
    render(<PasswordInput id="pw" value="" onChange={onChange} />);
    fireEvent.change(document.getElementById("pw") as HTMLInputElement, {
      target: { value: "abc" },
    });
    expect(onChange).toHaveBeenCalledWith("abc");
  });
});
