import { afterEach, describe, expect, it, vi } from "vitest";
import { copyText } from "./clipboard";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("テキストのクリップボードコピー", () => {
  it("空文字のときはコピーせず false を返すことを検証する", async () => {
    const spy = vi.fn();
    vi.stubGlobal("navigator", { clipboard: { writeText: spy } });
    expect(await copyText("")).toBe(false);
    expect(spy).not.toHaveBeenCalled();
  });

  it("コピーが成功すると true を返し、その文字列を渡すことを検証する", async () => {
    const spy = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText: spy } });
    expect(await copyText("ありがとう")).toBe(true);
    expect(spy).toHaveBeenCalledWith("ありがとう");
  });

  it("コピーが失敗したら握り潰さず false を返すことを検証する", async () => {
    const spy = vi.fn().mockRejectedValue(new Error("denied"));
    vi.stubGlobal("navigator", { clipboard: { writeText: spy } });
    expect(await copyText("ありがとう")).toBe(false);
  });
});
