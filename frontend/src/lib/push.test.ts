import { afterEach, describe, expect, it, vi } from "vitest";

import { enablePush, pushSupported, refreshPushToken } from "./push";

// Capacitor 本体とプラグインをモジュールごとモックする（camera.test.ts に倣う）。
const { nativeMock, pluginAvailableMock, pushMock } = vi.hoisted(() => ({
  nativeMock: vi.fn(),
  pluginAvailableMock: vi.fn(),
  pushMock: {
    requestPermissions: vi.fn(),
    checkPermissions: vi.fn(),
    register: vi.fn(),
    addListener: vi.fn(),
  },
}));
vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: nativeMock, isPluginAvailable: pluginAvailableMock },
}));
vi.mock("@capacitor/push-notifications", () => ({ PushNotifications: pushMock }));

function native(on: boolean) {
  nativeMock.mockReturnValue(on);
  pluginAvailableMock.mockReturnValue(on);
}

/** register() 呼び出し時に registration リスナーへトークンを流す。 */
function stubRegistration(token: string) {
  const listeners: Record<string, (arg: { value: string }) => void> = {};
  pushMock.addListener.mockImplementation((name: string, cb: (arg: { value: string }) => void) => {
    listeners[name] = cb;
  });
  pushMock.register.mockImplementation(() => {
    listeners.registration?.({ value: token });
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  for (const f of Object.values(pushMock)) f.mockReset();
});

describe("iOS プッシュ通知の有効化（#205）", () => {
  it("Web（非ネイティブ）ではサポート外で、有効化も何もしないことを検証する", async () => {
    native(false);
    expect(pushSupported()).toBe(false);
    const reg = vi.fn();
    expect(await enablePush(reg)).toBe(false);
    expect(reg).not.toHaveBeenCalled();
  });

  it("許可されるとトークンを取得してバックエンドに登録することを検証する", async () => {
    native(true);
    pushMock.requestPermissions.mockResolvedValue({ receive: "granted" });
    stubRegistration("apns-token-1");
    const reg = vi.fn().mockResolvedValue({ ok: true });
    expect(await enablePush(reg)).toBe(true);
    expect(reg).toHaveBeenCalledWith("apns-token-1");
  });

  it("許可が拒否されたら登録せず false を返すことを検証する", async () => {
    native(true);
    pushMock.requestPermissions.mockResolvedValue({ receive: "denied" });
    const reg = vi.fn();
    expect(await enablePush(reg)).toBe(false);
    expect(reg).not.toHaveBeenCalled();
    expect(pushMock.register).not.toHaveBeenCalled();
  });

  it("起動時の再登録は許可済みのときだけ行う（未許可でダイアログを出さない）ことを検証する", async () => {
    native(true);
    pushMock.checkPermissions.mockResolvedValue({ receive: "prompt" });
    const reg = vi.fn();
    await refreshPushToken(reg);
    expect(pushMock.requestPermissions).not.toHaveBeenCalled();
    expect(reg).not.toHaveBeenCalled();

    pushMock.checkPermissions.mockResolvedValue({ receive: "granted" });
    stubRegistration("apns-token-2");
    await refreshPushToken(reg);
    expect(reg).toHaveBeenCalledWith("apns-token-2");
  });
});
