"""LLM プロバイダ選択（_default_ocr）のテスト。環境変数で実装が切り替わることを検証する。"""

from app.adapters import BedrockOcrLlm, ClaudeAgentOcrLlm
from app.main import _default_ocr
from app.ports import OcrLlmMock


def test_default_ocrはclaude_agentでAgent実装を選ぶ(monkeypatch):
    monkeypatch.setenv("NOSHI_LLM_PROVIDER", "claude_agent")
    assert isinstance(_default_ocr(), ClaudeAgentOcrLlm)


def test_default_ocrはbedrockでBedrock実装を選ぶ(monkeypatch):
    monkeypatch.setenv("NOSHI_LLM_PROVIDER", "bedrock")
    assert isinstance(_default_ocr(), BedrockOcrLlm)


def test_default_ocrは後方互換でNOSHI_USE_BEDROCKを尊重する(monkeypatch):
    monkeypatch.delenv("NOSHI_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("NOSHI_USE_BEDROCK", "1")
    assert isinstance(_default_ocr(), BedrockOcrLlm)


def test_default_ocrは未設定ならモック(monkeypatch):
    monkeypatch.delenv("NOSHI_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("NOSHI_USE_BEDROCK", raising=False)
    assert isinstance(_default_ocr(), OcrLlmMock)
