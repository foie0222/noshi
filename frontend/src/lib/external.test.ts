import { Capacitor } from "@capacitor/core";
import { describe, expect, it, vi } from "vitest";
import { openExternalUrl } from "./external";

// Capacitor プラグインはプロキシ経由で解決されるため spyOn できない。モジュールごとモックする。
const { openMock } = vi.hoisted(() => ({ openMock: vi.fn(() => Promise.resolve()) }));
vi.mock("@capacitor/browser", () => ({ Browser: { open: openMock } }));

describe("openExternalUrl（外部リンクのネイティブ/Web 分岐 #230）", () => {
  it("Web では何も開かず false を返す（<a> の既定動作に任せる）", () => {
    const spy = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(false);
    expect(openExternalUrl("https://hb.afl.rakuten.co.jp/x")).toBe(false);
    expect(openMock).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it("空 URL は false（開かない）", () => {
    expect(openExternalUrl("")).toBe(false);
  });

  it("ネイティブでは Browser.open を呼び true を返す（preventDefault させる）", () => {
    openMock.mockClear();
    const spy = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    const url = "https://hb.afl.rakuten.co.jp/x";
    expect(openExternalUrl(url)).toBe(true);
    expect(openMock).toHaveBeenCalledWith({ url });
    spy.mockRestore();
  });
});
