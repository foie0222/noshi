import { Capacitor } from "@capacitor/core";
import { describe, expect, it, vi } from "vitest";

import { isNativePlatform } from "./platform";

describe("isNativePlatform（実行プラットフォーム判定）", () => {
  it("ネイティブ環境では true を返し Web 環境では false を返す", () => {
    const spy = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    expect(isNativePlatform()).toBe(true);
    spy.mockReturnValue(false);
    expect(isNativePlatform()).toBe(false);
    spy.mockRestore();
  });
});
