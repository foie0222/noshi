import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RelationshipField } from "./RelationshipField";

describe("RelationshipField（続柄の選択＋追加）", () => {
  const opts = ["親", "友人", "その他"];

  it("マスタの選択肢と未選択を表示することを検証する", () => {
    render(<RelationshipField value="" options={opts} onChange={() => {}} onAdd={() => {}} />);
    expect(screen.getByRole("option", { name: "親" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "未選択" })).toBeInTheDocument();
  });

  it("選択肢に無い既存値（自由入力/AI抽出）も表示することを検証する（後方互換）", () => {
    render(
      <RelationshipField value="元同僚" options={opts} onChange={() => {}} onAdd={() => {}} />,
    );
    // 現在値がオプションとして含まれ、選択されている
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("元同僚");
    expect(screen.getByRole("option", { name: "元同僚" })).toBeInTheDocument();
  });

  it("「追加」を選ぶと入力欄が現れ、確定で onAdd が呼ばれることを検証する", () => {
    const onAdd = vi.fn();
    render(<RelationshipField value="" options={opts} onChange={() => {}} onAdd={onAdd} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "__add__" } });
    const input = screen.getByPlaceholderText("新しい続柄");
    fireEvent.change(input, { target: { value: "ママ友" } });
    fireEvent.click(screen.getByRole("button", { name: "追加" }));
    expect(onAdd).toHaveBeenCalledWith("ママ友");
  });

  it("通常の選択は onChange に値を渡すことを検証する", () => {
    const onChange = vi.fn();
    render(<RelationshipField value="" options={opts} onChange={onChange} onAdd={() => {}} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "親" } });
    expect(onChange).toHaveBeenCalledWith("親");
  });
});
