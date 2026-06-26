"""Claude Agent SDK 経由のトランスポート（Claude Max サブスクリプション / OAuth）。

Bedrock を経由せず、`claude_agent_sdk` 越しに Claude へ 1 ターンだけ問い合わせる。
認証は Claude Code と同じ OAuth トークン（CLAUDE_CODE_OAUTH_TOKEN）。本番(Lambda)では
SSM SecureString から遅延取得し、ローカル開発ではログイン済み `claude` CLI のセッションを使う。

OCR/キュレーション共通の薄い層。プロンプト文・JSON 抽出・機械検証は呼び出し側に残し、
ここは「system + コンテンツブロック列 → 応答テキスト」だけを担う。

注意: Agent SDK は maxTokens/temperature を制御できない（Claude Code 由来）。出力長や
JSON 限定・決定性はプロンプト側の指示（「JSON のみ」「N字以内」等）に委ねる。
"""

from __future__ import annotations

import asyncio
import base64
import os
import threading
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

_token_loaded = False


def text_block(text: str) -> dict[str, Any]:
    """Anthropic 形式のテキストコンテンツブロック。"""
    return {"type": "text", "text": text}


def image_block(media_type: str, data: bytes) -> dict[str, Any]:
    """Anthropic 形式の base64 画像コンテンツブロック（media_type 例: image/jpeg）。"""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(data).decode(),
        },
    }


def _ensure_token() -> None:
    """OAuth トークンを環境に用意する（一度だけ）。

    CLAUDE_CODE_OAUTH_TOKEN が未設定でも NOSHI_CLAUDE_TOKEN_SSM があれば SSM から取得して
    展開する。どちらも無ければ何もしない（ローカルは `claude` CLI のログインに委ねる）。
    """
    global _token_loaded
    if _token_loaded:
        return
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        ssm_name = os.environ.get("NOSHI_CLAUDE_TOKEN_SSM")
        if ssm_name:
            import boto3  # 遅延 import（ローカル/テストでは不要）

            r = boto3.client("ssm").get_parameter(Name=ssm_name, WithDecryption=True)
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = str(r["Parameter"]["Value"])
    _token_loaded = True


async def _query_text(system: str, content: list[dict[str, Any]], model: str | None) -> str:
    """streaming 入力で 1 ユーザーメッセージを送り、AssistantMessage のテキストを連結して返す。"""
    options = ClaudeAgentOptions(
        system_prompt=system,
        allowed_tools=[],  # ツール無効（純粋なテキスト生成）
        # ツール無しなら 1 ターンで回答が確定するが、max_turns=1 だと稀に CLI が
        # "max turns" エラー結果を返す。余裕を持たせる（ツール無効なので追加ターンは消費されない）。
        max_turns=3,
        model=model or os.environ.get("NOSHI_CLAUDE_MODEL"),
    )

    async def _input() -> AsyncIterator[dict[str, Any]]:
        yield {
            "type": "user",
            "message": {"role": "user", "content": content},
            "parent_tool_use_id": None,
            "session_id": "noshi",
        }

    parts: list[str] = []
    async for msg in query(prompt=_input(), options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
    text = "".join(parts)
    if not text.strip():
        raise RuntimeError("Claude Agent SDK が空応答を返しました")
    return text


def _run_sync(coro: Any) -> str:
    """coroutine を専用スレッドの新規イベントループで実行する。

    呼び出し元が同期(Starlette のスレッドプール上の `def` ルート / バッチ)でも、稀に
    走行中ループがあっても衝突しないよう、必ず別スレッドで asyncio.run する。
    """
    box: dict[str, Any] = {}

    def _worker() -> None:
        try:
            box["value"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 - スレッド境界を越えて再送出する
            box["error"] = exc

    t = threading.Thread(target=_worker)
    t.start()
    t.join()
    if "error" in box:
        raise box["error"]
    return str(box["value"])


def run_query(system: str, content: list[dict[str, Any]], *, model: str | None = None) -> str:
    """system プロンプトとコンテンツブロック列を渡し、Claude の応答テキストを返す（同期 API）。

    content は Anthropic 形式のブロック列（text_block / image_block で生成）。
    """
    _ensure_token()
    return _run_sync(_query_text(system, content, model))
