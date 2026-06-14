#!/usr/bin/env python3
"""クラウド署名が毎ビルド作る使い捨て開発証明書を失効し、Apple の証明書上限到達を防ぐ（#196/#206）。

CI のリリースジョブ冒頭で実行する。`-allowProvisioningUpdates` 方式は CI の各ランナーで
秘密鍵が失われるため毎回新しい "Created via API" 証明書を作り、約16個で上限に達して
archive が "maximum number of certificates" で失敗する。前ビルドが作った証明書は秘密鍵が
既に無く再利用できないので、ビルド前にまとめて失効しても安全（このビルドが新たに1つ作る）。

環境変数: ASC_KEY_ID / ASC_ISSUER_ID / ASC_API_KEY_P8（App Store Connect API キー）。
依存: pyjwt, cryptography（CI 側で pip install）。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

import jwt

API = "https://api.appstoreconnect.apple.com/v1/certificates"
# 失効対象はクラウド署名が自動生成する証明書のみ。手動発行（ユーザー名など）は残す。
REVOKE_DISPLAY_NAME = "Created via API"


def _token() -> str:
    key_id = os.environ["ASC_KEY_ID"]
    issuer = os.environ["ASC_ISSUER_ID"]
    private_key = os.environ["ASC_API_KEY_P8"]
    now = int(time.time())
    return jwt.encode(
        {"iss": issuer, "iat": now, "exp": now + 600, "aud": "appstoreconnect-v1"},
        private_key,
        algorithm="ES256",
        headers={"kid": key_id},
    )


def _request(method: str, url: str, token: str) -> dict | None:
    req = urllib.request.Request(url, method=method, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def main() -> None:
    # トークンは 600s 有効。1回の実行（数秒）では使い回して十分なので一度だけ生成する。
    token = _token()
    resp = _request("GET", f"{API}?limit=200", token)
    data = (resp or {"data": []})["data"]  # 空ボディでも落とさない
    stale = [c for c in data if c["attributes"].get("displayName") == REVOKE_DISPLAY_NAME]
    print(f"certificates total={len(data)} stale('{REVOKE_DISPLAY_NAME}')={len(stale)}")
    revoked = 0
    for cert in stale:
        cid = cert["id"]
        try:
            _request("DELETE", f"{API}/{cid}", token)
            revoked += 1
            print(f"  revoked {cid}")
        except urllib.error.HTTPError as e:  # 失効失敗は致命ではない（ビルドは続行）
            print(f"  skip {cid}: HTTP {e.code}")
    print(f"revoked {revoked}/{len(stale)}; remaining={len(data) - revoked}")


if __name__ == "__main__":
    main()
