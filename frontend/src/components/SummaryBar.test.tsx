import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SummaryBar } from "./SummaryBar";

describe("SummaryBar コンポーネント", () => {
  it("もらった・あげた・差分の金額を画面に表示することを検証する", () => {
    render(<SummaryBar received={84000} given={39000} diff={45000} />);
    expect(screen.getByText("¥84,000")).toBeInTheDocument();
    expect(screen.getByText("¥39,000")).toBeInTheDocument();
    expect(screen.getByText("+¥45,000")).toBeInTheDocument();
  });
});
