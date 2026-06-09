import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RelationshipField } from "./RelationshipField";

const defaults = ["親", "友人", "その他"];

function setup(props: Partial<Parameters<typeof RelationshipField>[0]> = {}) {
  const onChange = vi.fn();
  const onAdd = vi.fn();
  const onDelete = vi.fn();
  render(
    <RelationshipField
      value={props.value ?? ""}
      options={props.options ?? defaults}
      defaults={props.defaults ?? defaults}
      onChange={onChange}
      onAdd={onAdd}
      onDelete={onDelete}
    />,
  );
  return { onChange, onAdd, onDelete };
}

describe("RelationshipField（続柄の選択＋追加＋削除）", () => {
  it("トリガーは現在値（未選択なら『未選択』）を表示し、開くと選択肢が出ることを検証する", () => {
    setup({ value: "" });
    const trigger = screen.getByRole("combobox");
    expect(trigger).toHaveTextContent("未選択");
    fireEvent.click(trigger);
    expect(screen.getByRole("option", { name: "親" })).toBeInTheDocument();
  });

  it("選択肢を選ぶと onChange に値を渡して閉じることを検証する", () => {
    const { onChange } = setup();
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("option", { name: "親" }));
    expect(onChange).toHaveBeenCalledWith("親");
    expect(screen.queryByRole("option", { name: "親" })).not.toBeInTheDocument(); // 閉じる
  });

  it("選択肢に無い既存値（自由入力/AI抽出/削除済み）も現在値として表示することを検証する（後方互換）", () => {
    setup({ value: "元同僚" });
    expect(screen.getByRole("combobox")).toHaveTextContent("元同僚");
    fireEvent.click(screen.getByRole("combobox"));
    expect(screen.getByRole("option", { name: "元同僚" })).toBeInTheDocument();
  });

  it("「追加」を選ぶと入力欄が現れ、確定で onAdd が呼ばれることを検証する", () => {
    const { onAdd } = setup();
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("option", { name: /新しい続柄を追加/ }));
    const input = screen.getByPlaceholderText("新しい続柄");
    fireEvent.change(input, { target: { value: "ママ友" } });
    fireEvent.click(screen.getByRole("button", { name: "追加" }));
    expect(onAdd).toHaveBeenCalledWith("ママ友");
  });

  it("世帯独自の続柄には削除ボタンがあり onDelete を呼ぶことを検証する", () => {
    const { onDelete } = setup({ options: [...defaults, "ママ友"] });
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("button", { name: "ママ友 を削除" }));
    expect(onDelete).toHaveBeenCalledWith("ママ友");
  });

  it("システム既定の続柄には削除ボタンが無いことを検証する", () => {
    setup();
    fireEvent.click(screen.getByRole("combobox"));
    expect(screen.queryByRole("button", { name: "親 を削除" })).not.toBeInTheDocument();
  });
});
