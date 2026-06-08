"""業務ルール（技術非依存）。functional-design/business-rules.md に対応。

- BR-HR: 半返しの用途別返礼率・1,000円丸め・上書き
- BR-EX: 抽出の信頼度しきい値
- BR-VAL: 贈答レコードの入力検証
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from app.domain.entities import GiftRecord

CONFIDENCE_THRESHOLD = 0.7

# 用途 → お返し期限の日数（受領日起点）。None はお返し不要。
_DUE_DAYS_DEFAULT = 30
_DUE_NONE = ("お中元", "お歳暮")


def due_date(occurred_at: str, purpose: str) -> datetime.date | None:
    """受領日と用途から標準お返し期限を算出する（BR-3-DUE）。お返し不要なら None。"""
    p = purpose or ""
    if any(k in p for k in _DUE_NONE):
        return None
    try:
        base = datetime.date.fromisoformat((occurred_at or "")[:10])
    except ValueError:
        base = datetime.date.today()  # occurred_at 未設定/不正は今日でフォールバック
    days = 49 if "香典" in p else _DUE_DAYS_DEFAULT
    return base + datetime.timedelta(days=days)


def days_left(due: datetime.date | None, today: datetime.date | None = None) -> int | None:
    """期限日と基準日から残日数を返す（超過は負値）。期限なしは None。"""
    if due is None:
        return None
    return (due - (today or datetime.date.today())).days


# 用途 → (推奨比率, レンジ下限比率)。お中元/お歳暮は返礼不要。
_DEFAULT_RATIO = 0.5
_GIFT_UNNEEDED = ("お中元", "お歳暮")
# 一般慶事（既定 1/3）に分類するキーワード
_GENERAL_KEYWORDS = ("入学", "新築", "新居", "卒業", "就職", "一般慶事")


@dataclass
class ReturnRange:
    """推奨お返し額の算出結果。"""

    recommended: int
    low: int
    high: int
    ratio: float
    rationale: str
    gift_unneeded: bool = False


def _round_to_1000(value: float) -> int:
    """1,000円単位に四捨五入（半数切り上げ）。"""
    return int(value / 1000 + 0.5) * 1000


def _ratio_for(purpose: str) -> tuple[float, float, str]:
    """用途から (推奨比率, レンジ下限比率, 根拠) を返す。"""
    p = purpose or ""
    if any(k in p for k in _GIFT_UNNEEDED):
        return 0.0, 0.0, "お中元・お歳暮は返礼不要。礼状でお礼を伝えます。"
    if "香典" in p:
        return 0.5, 0.5, "香典（弔事）は半返し（1/2）が目安です。"
    if "結婚" in p:
        return 0.5, 0.5, "結婚祝いは1/2が目安です（引出物がある場合は調整）。"
    if "出産" in p:
        return 0.5, 1 / 3, "出産祝いは1/3〜半返し（既定1/2）が目安です。"
    if "快気" in p:
        return 0.5, 1 / 3, "快気祝いは1/3〜半返し（既定1/2）が目安です。"
    if any(k in p for k in _GENERAL_KEYWORDS):
        return 1 / 3, 1 / 3, "入学・新築など一般慶事は1/3〜半返し（既定1/3）が目安です。"
    return _DEFAULT_RATIO, _DEFAULT_RATIO, "一般的な目安として半返し（1/2）で算出しました。"


def half_return(amount: int, purpose: str) -> ReturnRange:
    """もらった額と用途から推奨お返し額（レンジ）を算出する（BR-HR）。"""
    if amount is None or amount <= 0:
        raise ValueError("amount must be > 0")  # BR-HR-4
    ratio, low_ratio, rationale = _ratio_for(purpose)
    if ratio == 0.0:
        return ReturnRange(0, 0, 0, 0.0, rationale, gift_unneeded=True)
    recommended = _round_to_1000(amount * ratio)
    low = _round_to_1000(amount * low_ratio)
    high = _round_to_1000(amount * 0.5)
    return ReturnRange(recommended, min(low, recommended), max(high, recommended), ratio, rationale)


# 弔事キーワード（BR-4-TONE）。社会通念上の贈答で集計除外する用途（BR-4-TAX）。
_MOURNING_KEYWORDS = ("香典", "御霊前", "御仏前", "法事", "法要", "弔慰", "お悔やみ")
_GIFT_TAX_EXCLUDED = ("香典", "御霊前", "御仏前", "お中元", "お歳暮", "中元", "歳暮")
GIFT_TAX_EXEMPTION = 1_100_000  # 暦年課税の基礎控除


def tone(purpose: str) -> str:
    """用途を弔事(mourning)/慶事(celebration)に分類する（BR-4-TONE）。"""
    p = purpose or ""
    return "mourning" if any(k in p for k in _MOURNING_KEYWORDS) else "celebration"


def gift_tax_summary(records: list[GiftRecord], year: int) -> dict[str, Any]:
    """暦年の「もらった」対象合計と110万円枠への残額・超過を返す（BR-4-TAX）。

    社会通念上の贈答（香典・お中元・お歳暮等）と given・対象年外は集計から除外する。
    税アドバイスではなく概算の気づき。本人データのみを渡す前提（A01）。
    """
    total = 0
    for r in records:
        if getattr(r, "direction", "received") != "received":
            continue
        purpose = getattr(r, "purpose", "") or ""
        if any(k in purpose for k in _GIFT_TAX_EXCLUDED):
            continue
        occurred = (getattr(r, "occurred_at", "") or "")[:4]
        if occurred and occurred != str(year):
            continue
        total += getattr(r, "amount", 0) or 0
    return {
        "total": total,
        "remaining": max(0, GIFT_TAX_EXEMPTION - total),
        "over": total > GIFT_TAX_EXEMPTION,
        "exemption": GIFT_TAX_EXEMPTION,
        "year": year,
    }


def annual_summary(records: list[GiftRecord], year: int) -> dict[str, Any]:
    """指定年のやりとりを集計して年間振り返りを返す（本人データのみ）。

    occurred_at の先頭4桁が指定年のレコードのみを対象に、受領/あげたの件数・合計、
    やりとりした相手のユニーク人数を返す。日付不明（occurred_at 空）は対象外。
    """
    in_year = [r for r in records if (getattr(r, "occurred_at", "") or "")[:4] == str(year)]
    received = [r for r in in_year if getattr(r, "direction", "received") == "received"]
    given = [r for r in in_year if getattr(r, "direction", "received") == "given"]
    return {
        "year": year,
        "received_count": len(received),
        "received_total": sum((r.amount or 0) for r in received),
        "given_count": len(given),
        "given_total": sum((r.amount or 0) for r in given),
        "party_count": len({r.party_name for r in in_year}),
    }


RELATIONSHIP_ATTENTION_DAYS = 180  # 「気になる関係」の経過日数しきい値
_BALANCE_TOLERANCE = 0.2  # |差分|/総額 がこれ以下なら均衡


def relationship_balance(
    records: list[GiftRecord], today: datetime.date | None = None
) -> list[dict[str, Any]]:
    """相手別に もらった/あげた/差分/最終やりとり日 を集計し、偏りを分類する（BR-6-BALANCE）。

    損得ではなく「関係のメンテナンス」のための気づき。本人データのみを渡す前提（A01）。
    返り値は attention（気になる関係）優先・差分降順で並べる。
    """
    import datetime

    today = today or datetime.date.today()
    parties: dict[str, dict[str, Any]] = {}
    for r in records:
        name = getattr(r, "party_name", "") or ""
        if not name:
            continue
        p = parties.setdefault(name, {"party_name": name, "received": 0, "given": 0, "last_at": ""})
        amount = getattr(r, "amount", 0) or 0
        direction = getattr(r, "direction", "received")
        p["received" if direction == "received" else "given"] += amount
        occurred = (getattr(r, "occurred_at", "") or "")[:10]
        if occurred > p["last_at"]:
            p["last_at"] = occurred

    out = []
    for p in parties.values():
        total = p["received"] + p["given"]
        diff = p["received"] - p["given"]
        if total == 0 or abs(diff) <= total * _BALANCE_TOLERANCE:
            status = "balanced"
        elif diff > 0:
            status = "owe"  # もらい超過
        else:
            status = "ahead"  # あげ超過
        attention = False
        if status == "owe" and p["last_at"]:
            try:
                last = datetime.date.fromisoformat(p["last_at"])
                attention = (today - last).days > RELATIONSHIP_ATTENTION_DAYS
            except ValueError:
                attention = False
        out.append({**p, "diff": diff, "status": status, "attention": attention})

    out.sort(key=lambda b: (not b["attention"], -b["diff"]))
    return out


def needs_review(confidence: float, threshold: float = CONFIDENCE_THRESHOLD) -> bool:
    """抽出項目の信頼度がしきい値未満なら要確認（BR-EX-2）。"""
    return confidence < threshold


def validate_record(amount: int, purpose: str, party_name: str, direction: str) -> list[str]:
    """贈答レコードの入力検証。エラーメッセージの一覧を返す（BR-VAL）。"""
    errors: list[str] = []
    if amount is None or amount <= 0:
        errors.append("金額は1円以上を入力してください")
    if not (purpose or "").strip():
        errors.append("用途を入力してください")
    if not (party_name or "").strip():
        errors.append("お相手を入力してください")
    if direction not in ("received", "given"):
        errors.append("方向が不正です")
    return errors
