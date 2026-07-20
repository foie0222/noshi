import { afterEach, describe, expect, it, vi } from "vitest";

import { CameraPermissionDeniedError, captureNativePhoto } from "./camera";

// Capacitor プラグインはプロキシ解決のため spyOn 不可。モジュールごとモックする（external.test.ts に倣う）。
const { getPhotoMock, checkPermissionsMock } = vi.hoisted(() => ({
  getPhotoMock: vi.fn(),
  checkPermissionsMock: vi.fn(),
}));
vi.mock("@capacitor/camera", () => ({
  Camera: { getPhoto: getPhotoMock, checkPermissions: checkPermissionsMock },
  CameraResultType: { Uri: "uri" },
  CameraSource: { Prompt: "PROMPT", Camera: "CAMERA", Photos: "PHOTOS" },
}));

function grant(camera = "granted", photos = "granted") {
  checkPermissionsMock.mockResolvedValue({ camera, photos });
}

afterEach(() => {
  vi.restoreAllMocks();
  getPhotoMock.mockReset();
  checkPermissionsMock.mockReset();
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

    const file = await captureNativePhoto("camera");
    expect(file).toBeInstanceOf(File);
    expect(file?.type).toBe("image/jpeg");
    // iPad で OS のアクションシートが開けないため PROMPT は使わない（#402）。
    expect(getPhotoMock).toHaveBeenCalledWith(
      expect.objectContaining({
        source: "CAMERA",
        presentationStyle: "fullscreen",
        resultType: "uri",
        correctOrientation: true,
      }),
    );
    vi.unstubAllGlobals();
  });

  it("ユーザーがキャンセルしたら null を返す（エラーにしない）", async () => {
    grant();
    getPhotoMock.mockRejectedValue(new Error("User cancelled photos app"));
    await expect(captureNativePhoto("photos")).resolves.toBeNull();
  });

  it("撮影は成功したが webPath が無いときは null を返す（防御）", async () => {
    grant();
    getPhotoMock.mockResolvedValue({ webPath: undefined, format: "jpeg" });
    await expect(captureNativePhoto("photos")).resolves.toBeNull();
  });

  it("選んだソースの権限が denied のとき CameraPermissionDeniedError を投げる", async () => {
    grant("denied", "granted");
    await expect(captureNativePhoto("camera")).rejects.toBeInstanceOf(CameraPermissionDeniedError);
    expect(getPhotoMock).not.toHaveBeenCalled();
  });

  it("撮影が権限エラーで失敗したら CameraPermissionDeniedError を投げる", async () => {
    grant("prompt", "prompt");
    getPhotoMock.mockRejectedValue(new Error("User denied access to camera"));
    await expect(captureNativePhoto("camera")).rejects.toBeInstanceOf(CameraPermissionDeniedError);
  });

  it("カメラ拒否でも写真ライブラリ（photos）は選択に進める", async () => {
    grant("denied", "granted");
    getPhotoMock.mockResolvedValue({ webPath: "blob:fake/xyz", format: "png" });
    const blob = new Blob([new Uint8Array(5)], { type: "image/png" });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ blob: () => Promise.resolve(blob) })),
    );
    const file = await captureNativePhoto("photos");
    expect(file).toBeInstanceOf(File);
    expect(getPhotoMock).toHaveBeenCalledWith(expect.objectContaining({ source: "PHOTOS" }));
    vi.unstubAllGlobals();
  });
});
