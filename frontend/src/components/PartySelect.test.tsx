import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Party } from "../types";
import { PartySelect } from "./PartySelect";

const parties: Party[] = [
  { id: "p1", name: "田中", relationship: "友人" },
  { id: "p2", name: "田中", relationship: "会社" },
];

function setup(props: Partial<Parameters<typeof PartySelect>[0]> = {}) {
  const onChange = vi.fn();
  const onAdd = vi.fn();
  render(
    <PartySelect
      value={props.value ?? ""}
      parties={props.parties ?? parties}
      onChange={onChange}
      onAdd={onAdd}
      suggestedName={props.suggestedName ?? ""}
      relOptions={["友人", "会社", "その他"]}
      relDefaults={["友人", "会社", "その他"]}
      onAddRelationship={() => {}}
      onDeleteRelationship={() => {}}
    />,
  );
  return { onChange, onAdd };
}

describe("PartySelect（相手の選択・同名は続柄で区別）", () => {
  it("同名の相手を続柄付きで区別表示することを検証する（#47）", () => {
    setup();
    fireEvent.click(screen.getByRole("combobox"));
    expect(screen.getByRole("option", { name: "田中（友人）" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "田中（会社）" })).toBeInTheDocument();
  });

  it("相手を選ぶと onChange に party_id を渡すことを検証する", () => {
    const { onChange } = setup();
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("option", { name: "田中（会社）" }));
    expect(onChange).toHaveBeenCalledWith("p2");
  });

  it("選択中の相手をトリガーに表示することを検証する", () => {
    setup({ value: "p1" });
    expect(screen.getByRole("combobox")).toHaveTextContent("田中（友人）");
  });

  it("「新しい相手を追加」で名前を入れて確定すると onAdd が呼ばれることを検証する", () => {
    const { onAdd } = setup({ suggestedName: "佐藤" });
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("option", { name: /新しい相手を追加/ }));
    const input = screen.getByPlaceholderText("相手のお名前");
    expect(input).toHaveValue("佐藤"); // OCR 名がプレフィル
    fireEvent.click(screen.getByRole("button", { name: "この相手で追加" }));
    expect(onAdd).toHaveBeenCalledWith("佐藤", "");
  });
});
