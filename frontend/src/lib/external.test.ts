import { afterEach, describe, expect, it, vi } from "vitest";

import { openExternal } from "./external";

// Capacitor 本体とブラウザプラグインをモジュールごとモックする（push.test.ts に倣う）。
const { nativeMock, browserMock } = vi.hoisted(() => ({
  nativeMock: vi.fn(),
  browserMock: { open: vi.fn() },
}));
vi.mock("@capacitor/core", () => ({ Capacitor: { isNativePlatform: nativeMock } }));
vi.mock("@capacitor/browser", () => ({ Browser: browserMock }));

afterEach(() => {
  vi.clearAllMocks();
});

describe("openExternal", () => {
  it("ネイティブではシステムのブラウザで開く", async () => {
    // アプリ内 WebView に読み込ませると楽天から戻れなくなる
    nativeMock.mockReturnValue(true);
    browserMock.open.mockResolvedValue(undefined);
    await openExternal("https://hb.afl.rakuten.co.jp/hgc/x");
    expect(browserMock.open).toHaveBeenCalledWith({ url: "https://hb.afl.rakuten.co.jp/hgc/x" });
  });

  it("Webでは別タブで開きプラグインを使わない", async () => {
    nativeMock.mockReturnValue(false);
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    await openExternal("https://hb.afl.rakuten.co.jp/hgc/x");
    expect(open).toHaveBeenCalledWith(
      "https://hb.afl.rakuten.co.jp/hgc/x",
      "_blank",
      "noopener,noreferrer",
    );
    expect(browserMock.open).not.toHaveBeenCalled();
    open.mockRestore();
  });

  it("httpsでないURLは開かない", async () => {
    // JSON が差し替えられても javascript: 等を実行させない
    nativeMock.mockReturnValue(true);
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    await openExternal("javascript:alert(1)");
    expect(browserMock.open).not.toHaveBeenCalled();
    expect(open).not.toHaveBeenCalled();
    open.mockRestore();
  });

  it("プラグインが失敗しても例外を投げない", async () => {
    // リンクが開けなかっただけで画面を壊さない
    nativeMock.mockReturnValue(true);
    browserMock.open.mockRejectedValue(new Error("no browser"));
    await expect(openExternal("https://hb.afl.rakuten.co.jp/hgc/x")).resolves.toBeUndefined();
  });
});
