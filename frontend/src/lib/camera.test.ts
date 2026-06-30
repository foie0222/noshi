import { Capacitor } from "@capacitor/core";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CameraPermissionDeniedError, captureNativePhoto, isNativeCamera } from "./camera";

// Capacitor プラグインはプロキシ解決のため spyOn 不可。モジュールごとモックする（external.test.ts に倣う）。
const { getPhotoMock, checkPermissionsMock } = vi.hoisted(() => ({
  getPhotoMock: vi.fn(),
  checkPermissionsMock: vi.fn(),
}));
vi.mock("@capacitor/camera", () => ({
  Camera: { getPhoto: getPhotoMock, checkPermissions: checkPermissionsMock },
  CameraResultType: { Uri: "uri" },
  CameraSource: { Prompt: "PROMPT" },
}));

function grant(camera = "granted", photos = "granted") {
  checkPermissionsMock.mockResolvedValue({ camera, photos });
}

afterEach(() => {
  vi.restoreAllMocks();
  getPhotoMock.mockReset();
  checkPermissionsMock.mockReset();
});

describe("isNativeCamera（ネイティブ判定）", () => {
  it("Capacitor.isNativePlatform を反映する", () => {
    const spy = vi.spyOn(Capacitor, "isNativePlatform").mockReturnValue(true);
    expect(isNativeCamera()).toBe(true);
    spy.mockReturnValue(false);
    expect(isNativeCamera()).toBe(false);
    spy.mockRestore();
  });
});

describe("captureNativePhoto（ネイティブ撮影）", () => {
  it("撮影成功時は webPath を取得して File を返す", async () => {
    grant();
    getPhotoMock.mockResolvedValue({ webPath: "blob:fake/abc", format: "jpeg" });
    const blob = new Blob([new Uint8Array(10)], { type: "image/jpeg" });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ blob: () => Promise.resolve(blob) })),
    );

    const file = await captureNativePhoto();
    expect(file).toBeInstanceOf(File);
    expect(file?.type).toBe("image/jpeg");
    expect(getPhotoMock).toHaveBeenCalledWith(
      expect.objectContaining({ source: "PROMPT", resultType: "uri", correctOrientation: true }),
    );
    vi.unstubAllGlobals();
  });

  it("ユーザーがキャンセルしたら null を返す（エラーにしない）", async () => {
    grant();
    getPhotoMock.mockRejectedValue(new Error("User cancelled photos app"));
    await expect(captureNativePhoto()).resolves.toBeNull();
  });

  it("カメラ・写真の両権限が denied のとき CameraPermissionDeniedError を投げる", async () => {
    grant("denied", "denied");
    await expect(captureNativePhoto()).rejects.toBeInstanceOf(CameraPermissionDeniedError);
    expect(getPhotoMock).not.toHaveBeenCalled();
  });

  it("撮影が権限エラーで失敗したら CameraPermissionDeniedError を投げる", async () => {
    grant("prompt", "prompt");
    getPhotoMock.mockRejectedValue(new Error("User denied access to camera"));
    await expect(captureNativePhoto()).rejects.toBeInstanceOf(CameraPermissionDeniedError);
  });

  it("カメラ拒否でも写真ライブラリが使えるなら撮影に進む", async () => {
    grant("denied", "granted");
    getPhotoMock.mockResolvedValue({ webPath: "blob:fake/xyz", format: "png" });
    const blob = new Blob([new Uint8Array(5)], { type: "image/png" });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ blob: () => Promise.resolve(blob) })),
    );
    const file = await captureNativePhoto();
    expect(file).toBeInstanceOf(File);
    vi.unstubAllGlobals();
  });
});
