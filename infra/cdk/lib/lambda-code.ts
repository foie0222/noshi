import * as lambda from "aws-cdk-lib/aws-lambda";
import { execSync } from "child_process";
import * as path from "path";
import * as fs from "fs";

/**
 * backend/ を依存ライブラリ込みで Lambda 用にバンドルする。
 *
 * 既定の Code.fromAsset はソースのみで fastapi/mangum 等が無く起動しないため、
 * pip で Lambda(Amazon Linux, x86_64, py3.12) 互換の wheel を同梱し、app/ をコピーする。
 * Docker 不要のローカルバンドル（ホストの pip3 を使用）。
 */
export function backendLambdaCode(): lambda.AssetCode {
  const backend = path.resolve(__dirname, "../../../backend");
  return lambda.Code.fromAsset(backend, {
    exclude: [".venv", "__pycache__", "**/__pycache__", "tests", ".pytest_cache", "*.md", ".lambda*"],
    bundling: {
      image: lambda.Runtime.PYTHON_3_12.bundlingImage, // Docker フォールバック用
      local: {
        tryBundle(outputDir: string): boolean {
          try {
            execSync("pip3 --version", { stdio: "ignore" });
          } catch {
            return false; // pip 無ければ Docker にフォールバック
          }
          execSync(
            [
              `pip3 install -r "${path.join(backend, "requirements.txt")}" ` +
                `--platform manylinux2014_x86_64 --implementation cp --python-version 3.12 ` +
                `--only-binary=:all: --upgrade --target "${outputDir}"`,
              `cp -r "${path.join(backend, "app")}" "${path.join(outputDir, "app")}"`,
            ].join(" && "),
            { stdio: "inherit" },
          );
          // uvicorn はサーバ用で Lambda 不要——容量削減のため除去（任意）
          fs.rmSync(path.join(outputDir, "uvicorn"), { recursive: true, force: true });
          return true;
        },
      },
    },
  });
}
