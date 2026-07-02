#!/usr/bin/env python3
"""App Store Connect API で App ID(Bundle ID) を登録し capability を有効化する（#210/#204）。

UI ログインなしで実施できる Apple 側作業を自動化する。実行は GitHub Actions
（ASC API キーは repo secrets）。冪等: 既に存在すれば作成/有効化をスキップする。

必要な環境変数（secrets 由来）:
  ASC_KEY_ID / ASC_ISSUER_ID / ASC_API_KEY_P8(生PEM) / APPLE_TEAM_ID
設定:
  BUNDLE_ID = me.noshi.app（capacitor.config・ios-release.yml と一致）
  有効化 capability = SIGN_IN_WITH_APPLE（App.entitlements と一致。push は #205 未実装のため付けない）
"""

import json
import os
import time
import urllib.error
import urllib.request

import jwt

BUNDLE_ID = "me.noshi.app"
BUNDLE_NAME = "noshi"
CAPABILITIES = ["APPLE_ID_AUTH"]  # ASC API 上の Sign in with Apple の capabilityType
BASE = "https://api.appstoreconnect.apple.com"


def make_token() -> str:
    key_id = os.environ["ASC_KEY_ID"]
    issuer = os.environ["ASC_ISSUER_ID"]
    private_key = os.environ["ASC_API_KEY_P8"]
    now = int(time.time())
    return jwt.encode(
        {"iss": issuer, "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"},
        private_key,
        algorithm="ES256",
        headers={"kid": key_id, "typ": "JWT"},
    )


def api(token: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else {})


def main() -> int:
    token = make_token()

    # 1. 既存の App ID を探す（capability も含めて取得）。
    st, res = api(
        token,
        "GET",
        f"/v1/bundleIds?filter[identifier]={BUNDLE_ID}&include=bundleIdCapabilities&limit=1",
    )
    if st != 200:
        print(f"[ERROR] bundleIds 取得に失敗: HTTP {st} {json.dumps(res)}")
        return 1

    items = res.get("data", [])
    if items:
        bundle = items[0]
        print(f"[OK] App ID は既に存在: {BUNDLE_ID} (id={bundle['id']})")
    else:
        st, res = api(
            token,
            "POST",
            "/v1/bundleIds",
            {
                "data": {
                    "type": "bundleIds",
                    "attributes": {
                        "identifier": BUNDLE_ID,
                        "name": BUNDLE_NAME,
                        "platform": "IOS",
                    },
                }
            },
        )
        if st not in (200, 201):
            print(f"[ERROR] App ID 作成に失敗: HTTP {st} {json.dumps(res)}")
            return 1
        bundle = res["data"]
        print(f"[CREATED] App ID を作成: {BUNDLE_ID} (id={bundle['id']})")

    bundle_id = bundle["id"]

    # 2. 現在有効な capability を確認。
    st, res = api(token, "GET", f"/v1/bundleIds/{bundle_id}/bundleIdCapabilities")
    if st != 200:
        print(f"[ERROR] capability 取得に失敗: HTTP {st} {json.dumps(res)}")
        return 1
    enabled = {c["attributes"]["capabilityType"] for c in res.get("data", [])}
    print(f"[INFO] 有効な capability: {sorted(enabled) or 'なし'}")

    # 3. 不足している capability を有効化。
    for cap in CAPABILITIES:
        if cap in enabled:
            print(f"[OK] {cap} は既に有効")
            continue
        st, res = api(
            token,
            "POST",
            "/v1/bundleIdCapabilities",
            {
                "data": {
                    "type": "bundleIdCapabilities",
                    "attributes": {"capabilityType": cap},
                    "relationships": {
                        "bundleId": {"data": {"type": "bundleIds", "id": bundle_id}}
                    },
                }
            },
        )
        if st not in (200, 201):
            print(f"[ERROR] {cap} の有効化に失敗: HTTP {st} {json.dumps(res)}")
            return 1
        print(f"[ENABLED] {cap} を有効化")

    print(f"\n[DONE] App ID {BUNDLE_ID} の登録と capability 設定が完了しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
