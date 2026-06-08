import { describe, expect, it } from "vitest";
import { MAX_IMAGE_BYTES, validateImageFile } from "./image";

function _fakeFile(type: string, size: number): File {
  // size バイトのダミー（中身は問わない）
  const blob = new Blob([new Uint8Array(Math.min(size, 1024))], { type });
  return new File([blob], "x", { type, lastModified: 0 }) as File & { size: number };
}

describe("画像ファイルの検証（BR-VAL-1）", () => {
  it("JPEG/PNG/HEIC は許可されることを検証する", () => {
    for (const t of ["image/jpeg", "image/png", "image/heic"]) {
      expect(validateImageFile({ type: t, size: 1000 } as File)).toBeNull();
    }
  });
  it("対応外の形式はエラーメッセージを返すことを検証する", () => {
    const err = validateImageFile({ type: "application/pdf", size: 1000 } as File);
    expect(err).toBeTruthy();
  });
  it("最大サイズ(10MB)を超えるとエラーになることを検証する", () => {
    const err = validateImageFile({ type: "image/jpeg", size: MAX_IMAGE_BYTES + 1 } as File);
    expect(err).toBeTruthy();
  });
  it("ファイル未選択(null)はエラーメッセージを返すことを検証する", () => {
    expect(validateImageFile(null)).toBeTruthy();
  });
});
