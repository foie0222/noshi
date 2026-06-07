"""デモ用シード。稼働中の API に demo-user の贈答記録を投入する（再現可能なデモ環境）。

使い方: backend を起動した状態で `.venv/bin/python seed_demo.py`
（API のベースURLは NOSHI_API 環境変数で上書き可、既定 http://localhost:8000）
"""
import json
import os
import urllib.request

BASE = os.environ.get("NOSHI_API", "http://localhost:8000")
HEADERS = {"Content-Type": "application/json", "X-User-Id": "demo-user"}

# occurred_at は当年(2026)を含め、年間振り返り・期限ダッシュボードが映えるよう配置。
RECORDS = [
    {"amount": 30000, "purpose": "出産祝い", "party_name": "叔母 佳子", "direction": "received", "occurred_at": "2026-05-20", "relationship": "親族"},
    {"amount": 10000, "purpose": "香典", "party_name": "近藤 様", "direction": "received", "occurred_at": "2026-05-28", "relationship": "知人"},
    {"amount": 50000, "purpose": "結婚祝い", "party_name": "高橋 健一", "direction": "received", "occurred_at": "2026-04-10", "relationship": "友人"},
    {"amount": 5000, "purpose": "お中元", "party_name": "前田 様", "direction": "received", "occurred_at": "2026-06-01", "relationship": "仕事"},
    {"amount": 20000, "purpose": "入学祝い", "party_name": "妹 美咲", "direction": "given", "occurred_at": "2026-03-15", "relationship": "親族"},
    {"amount": 8000, "purpose": "お年賀", "party_name": "叔母 佳子", "direction": "given", "occurred_at": "2026-01-02", "relationship": "親族"},
    {"amount": 15000, "purpose": "快気祝い", "party_name": "山本 様", "direction": "received", "occurred_at": "2026-02-08", "relationship": "知人"},
]


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}/api{path}", data=json.dumps(body).encode(), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read())


def main() -> None:
    for r in RECORDS:
        rec = post("/records", r)["record"]
        print(f"  + {rec['party_name']}  {r['purpose']}  {r['amount']:,}円  ({r['direction']})")
    print(f"投入完了: {len(RECORDS)}件 → demo-user")


if __name__ == "__main__":
    main()
