import { Capacitor } from "@capacitor/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearToken, getToken, hydrateToken, setToken } from "./tokenStore";

// SecureStorage（Keychain）はネイティブ専用プラグイン。Web/テストではモジュールごとモックする。
const { getItemMock, setItemMock, removeItemMock } = vi.hoisted(() => ({
  getItemMock: vi.fn(),
  setItemMock: vi.fn(() => Promise.resolve()),
  removeItemMock: vi.fn(() => Promise.resolve()),
}));
vi.mock("@aparajita/capacitor-secure-storage", () => ({
  SecureStorage: { getItem: getItemMock, setItem: setItemMock, removeItem: removeItemMock },
}));

function setNative(v: boolean) {
  return vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(v);
}

beforeEach(() => {
  localStorage.clear();
  getItemMock.mockReset();
  setItemMock.mockClear();
  removeItemMock.mockClear();
});
afterEach(() => {
  // clearToken を先に呼ぶ: restoreAllMocks 後だと isNative() が false になり
  // 非ネイティブパスで動いて in-memory cache が残る（テスト間リーク）。
  clearToken();
  vi.restoreAllMocks();
});

describe("tokenStore（Web: localStorage 同期）", () => {
  it("setToken は localStorage に保存し getToken で同期取得できる", () => {
    setNative(false);
    setToken("abc");
    expect(localStorage.getItem("noshi-id-token")).toBe("abc");
    expect(getToken()).toBe("abc");
    expect(setItemMock).not.toHaveBeenCalled();
  });

  it("clearToken は localStorage から消す", () => {
    setNative(false);
    setToken("abc");
    clearToken();
    expect(localStorage.getItem("noshi-id-token")).toBeNull();
    expect(getToken()).toBe("");
  });

  it("Web では hydrateToken は SecureStorage を触らない", async () => {
    setNative(false);
    await hydrateToken();
    expect(getItemMock).not.toHaveBeenCalled();
  });
});

describe("tokenStore（ネイティブ: Keychain + 同期キャッシュ）", () => {
  it("setToken は Keychain に書き、getToken はキャッシュから同期で返す", () => {
    setNative(true);
    setToken("tok-native");
    expect(setItemMock).toHaveBeenCalledWith("noshi-id-token", "tok-native");
    expect(getToken()).toBe("tok-native");
    expect(localStorage.getItem("noshi-id-token")).toBeNull(); // Web ストレージは使わない
  });

  it("hydrateToken は Keychain の値をキャッシュへ載せる", async () => {
    setNative(true);
    getItemMock.mockResolvedValue("restored");
    await hydrateToken();
    expect(getItemMock).toHaveBeenCalledWith("noshi-id-token");
    expect(getToken()).toBe("restored");
  });

  it("hydrateToken は Keychain が空/失敗でも空文字にフォールバックする", async () => {
    setNative(true);
    getItemMock.mockRejectedValue(new Error("keychain error"));
    await hydrateToken();
    expect(getToken()).toBe("");
  });

  it("clearToken は Keychain から消しキャッシュも空にする", () => {
    setNative(true);
    setToken("tok-native");
    clearToken();
    expect(removeItemMock).toHaveBeenCalledWith("noshi-id-token");
    expect(getToken()).toBe("");
  });
});
