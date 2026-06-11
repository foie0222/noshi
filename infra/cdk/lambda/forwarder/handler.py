"""SES 受信メールを Gmail 等へ転送する Lambda（#135）。

SES の受信ルールで S3 に保存された生メールを取得し、From を運営アドレスに
書き換えて転送する（Reply-To に元の送信者を残す）。送信元は検証済みドメイン
（noshi.me）なので SES から送信できる。
"""

from __future__ import annotations

import email
import os
from email.utils import parseaddr
from typing import Any

import boto3

s3 = boto3.client("s3")
ses = boto3.client("ses")

BUCKET = os.environ["BUCKET"]
PREFIX = os.environ.get("PREFIX", "inbound/")
FORWARD_TO = os.environ["FORWARD_TO"]
SENDER = os.environ["SENDER"]  # 例: contact@noshi.me


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    for record in event.get("Records", []):
        msg_id = record.get("ses", {}).get("mail", {}).get("messageId")
        if not msg_id:
            continue
        raw = s3.get_object(Bucket=BUCKET, Key=f"{PREFIX}{msg_id}")["Body"].read()
        msg = email.message_from_bytes(raw)

        orig_from = msg.get("From", "")
        reply_to = parseaddr(orig_from)[1] or SENDER
        # 転送のため送信元系ヘッダを除去し、検証済みドメインから送り直す。
        for header in ("DKIM-Signature", "Return-Path", "Sender", "From", "Reply-To", "Message-ID"):
            while header in msg:
                del msg[header]
        msg["From"] = f"noshi お問い合わせ <{SENDER}>"
        msg["Reply-To"] = reply_to
        if not msg.get("To"):
            msg["To"] = FORWARD_TO

        ses.send_raw_email(
            Source=SENDER,
            Destinations=[FORWARD_TO],
            RawMessage={"Data": msg.as_bytes()},
        )
    return {"ok": True}
