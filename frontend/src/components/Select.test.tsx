import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Select } from "./Select";

const opts = [
  { value: "date_desc", label: "新しい順" },
  { value: "date_asc", label: "古い順" },
  { value: "amount_desc", label: "金額が高い順" },
];

describe("Select（デザインシステム準拠の自前ドロップダウン）", () => {
  it("現在値のラベルをトリガーに表示することを検証する", () => {
    render(<Select value="amount_desc" options={opts} onChange={() => {}} ariaLabel="並べ替え" />);
    expect(screen.getByRole("combobox")).toHaveTextContent("金額が高い順");
  });

  it("トリガーを押すと選択肢が開くことを検証する", () => {
    render(<Select value="date_desc" options={opts} onChange={() => {}} ariaLabel="並べ替え" />);
    expect(screen.queryByRole("option", { name: "古い順" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("combobox"));
    expect(screen.getByRole("option", { name: "古い順" })).toBeInTheDocument();
  });

  it("選択肢を選ぶと onChange がその値で呼ばれ、閉じることを検証する", () => {
    const onChange = vi.fn();
    render(<Select value="date_desc" options={opts} onChange={onChange} ariaLabel="並べ替え" />);
    fireEvent.click(screen.getByRole("combobox"));
    fireEvent.click(screen.getByRole("option", { name: "古い順" }));
    expect(onChange).toHaveBeenCalledWith("date_asc");
    expect(screen.queryByRole("option", { name: "古い順" })).not.toBeInTheDocument();
  });

  it("選択中の項目に aria-selected が付くことを検証する", () => {
    render(<Select value="date_asc" options={opts} onChange={() => {}} ariaLabel="並べ替え" />);
    fireEvent.click(screen.getByRole("combobox"));
    expect(screen.getByRole("option", { name: "古い順" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("option", { name: "新しい順" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
  });
});
