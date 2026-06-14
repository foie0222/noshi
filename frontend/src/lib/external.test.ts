import { Browser } from "@capacitor/browser";
import { Capacitor } from "@capacitor/core";
import { describe, expect, it, vi } from "vitest";
import { openExternalUrl } from "./external";

describe("openExternalUrl（外部リンクのネイティブ/Web 分岐 #230）", () => {
  it("Web では何も開かず false を返す（<a> の既定動作に任せる）", () => {
    vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(false);
    expect(openExternalUrl("https://hb.afl.rakuten.co.jp/x")).toBe(false);
  });

  it("空 URL は false（開かない）", () => {
    expect(openExternalUrl("")).toBe(false);
  });

  it("ネイティブでは Browser.open を呼び true を返す（preventDefault させる）", () => {
    const native = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    const open = vi.spyOn(Browser, "open").mockResolvedValue();
    const url = "https://hb.afl.rakuten.co.jp/x";
    expect(openExternalUrl(url)).toBe(true);
    expect(open).toHaveBeenCalledWith({ url });
    native.mockRestore();
    open.mockRestore();
  });
});
