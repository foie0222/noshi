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


class JoinHouseholdIn(BaseModel):
    code: str = Field(min_length=1, description="家族から共有された招待コード")


class CaptureIn(BaseModel):
    # 撮影/選択画像（data URL もしくは base64）。未指定ならモック抽出にフォールバック。
    image: str | None = None


class RecordUpdateIn(BaseModel):
    amount: int = Field(gt=0, description="修正後の金額（>0）")
    purpose: str = Field(min_length=1)
    party_name: str = Field(min_length=1)
    # 未指定(None)なら既存値を保持する。"" を渡すと明示的にクリアできる。
    occurred_at: str | None = None
    relationship: str | None = None


class StatusIn(BaseModel):
    # considering は表示上「対応中」（発注・手配・準備中）。キーは互換のため据え置き（#4）。
    status: str = Field(pattern="^(received|considering|done)$")


class DueIn(BaseModel):
    # お返し期限の手動上書き。null/"" で上書き解除（自動計算へ戻す）。
    due_at: str | None = None


class RelationshipIn(BaseModel):
    # 世帯独自の続柄の追加（#1）。
    name: str = Field(min_length=1, description="追加する続柄")


class SelectSuggestionIn(BaseModel):
    title: str
    summary: str = ""
    external_ref: str = ""
    price_band: str = ""
