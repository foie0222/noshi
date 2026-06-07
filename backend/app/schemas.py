"""API 入出力スキーマ（pydantic）。入力検証はエッジ（A03）で行う。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RecordIn(BaseModel):
    amount: int = Field(gt=0, description="もらった/あげた金額（>0）")
    purpose: str = Field(min_length=1)
    party_name: str = Field(min_length=1)
    direction: str = Field(pattern="^(received|given)$")
    occurred_at: str = ""
    relationship: str = ""


class RecordUpdateIn(BaseModel):
    amount: int = Field(gt=0, description="修正後の金額（>0）")
    purpose: str = Field(min_length=1)
    party_name: str = Field(min_length=1)
    # 未指定(None)なら既存値を保持する。"" を渡すと明示的にクリアできる。
    occurred_at: str | None = None
    relationship: str | None = None


class StatusIn(BaseModel):
    status: str = Field(pattern="^(received|considering|done)$")


class SelectSuggestionIn(BaseModel):
    title: str
    summary: str = ""
    external_ref: str = ""
    price_band: str = ""


class LetterIn(BaseModel):
    purpose: str
    relationship: str = ""
    tone: str = "丁寧"
