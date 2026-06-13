"""お返し期限のリマインド（#178）。

「お返しを忘れない」を、ユーザーの記憶力に頼らず実現する。日次バッチ（EventBridge →
Lambda）が全世帯を走査し、お返し期限が **3日前・当日** のイベントを抽出して、世帯の
メンバーへ落ち着いたトーンのメール（SES）を1通送る。

設計方針:
  - 純粋ロジック（抽出・冪等判定）と副作用（SES送信）を分離し、AWS なしでテスト可能に。
  - 同じイベントの同日リマインドは重複送信しない（送信済みマーカーで冪等）。
  - 受け取りたくないメンバーには送らない（Membership.notify_email）。
  - メール本文はデザインシステム（生成り×明朝×朱）に準拠（frontend/tokens を写経）。
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .domain import rules
from .domain.entities import GiftEvent

if TYPE_CHECKING:
    from .repository import Repository

# お返し期限の何日前・当日に知らせるか。急かさないよう、超過は通知しない。
REMIND_OFFSETS = (3, 0)

SUBJECT = "noshi｜お返しの時期が近づいています"

# 送信コールバック: (to, subject, html) を受け取り1通送る。テストでは差し替える。
SendFn = Callable[[str, str, str], None]


@dataclass
class DueReminder:
    """リマインド対象1件（相手・用途・金額・期限・残日数）。"""

    event_id: str
    party_name: str
    purpose: str
    amount: int
    due: datetime.date
    days_left: int


def _resolve_due(ev: GiftEvent, occurred_at: str, purpose: str) -> datetime.date | None:
    """手動上書きを優先し、なければ用途・受領日からの既定期限を返す。"""
    override = ev.override_due
    if override:
        try:
            return datetime.date.fromisoformat(override[:10])
        except ValueError:
            pass
    return rules.due_date(occurred_at, purpose)


def collect_household_due(repo: Repository, scope: str, today: datetime.date) -> list[DueReminder]:
    """世帯スコープの未完了イベントから、期限が3日前・当日の「もらった」分を抽出する。"""
    out: list[DueReminder] = []
    for ev in repo.list_pending_events(scope):
        if ev.status == "done":
            continue
        rec = repo.get_record(scope, ev.record_id)
        if rec is None or rec.direction != "received":
            continue
        due = _resolve_due(ev, rec.occurred_at, rec.purpose)
        if due is None:
            continue
        days_left = (due - today).days
        if days_left not in REMIND_OFFSETS:
            continue
        # 相手名は人(Party)から最新を引く。なければ記録の名前。
        party = repo.get_party(scope, rec.party_id) if rec.party_id else None
        name = party.name if party else rec.party_name
        out.append(DueReminder(ev.id, name, rec.purpose, rec.amount, due, days_left))
    return out


def run_reminders(repo: Repository, today: datetime.date, send: SendFn) -> int:
    """全世帯を走査し、対象メンバーへリマインドを送る。送った通数を返す。

    同日・同イベントの重複は送らない。送信に成功したイベントだけを送信済みに記録する。
    """
    day = today.isoformat()
    sent_count = 0
    for h in repo.list_all_households():
        scope = h.id
        dues = collect_household_due(repo, scope, today)
        fresh = [d for d in dues if not repo.reminder_marked(scope, d.event_id, day)]
        if not fresh:
            continue
        members = [m for m in repo.list_members(scope) if m.email and m.notify_email]
        if not members:
            continue
        subject, html = render_reminder_email(fresh, today)
        for m in members:
            send(m.email, subject, html)
            sent_count += 1
        for d in fresh:
            repo.mark_reminder(scope, d.event_id, day)
    return sent_count


# --- メール本文（デザインシステム準拠 HTML） --------------------------------

_KINARI = "#F3EEE2"
_WASHI_RAISED = "#FFFDF8"
_SUMI = "#23211C"
_SUMI_SUB = "#5E574A"
_SUMI_MUTED = "#8A8270"
_SHU = "#B23A2E"
_KON = "#1F3A5A"
_BORDER_FAINT = "#E7DFCC"
_SERIF = "'Shippori Mincho B1','Hiragino Mincho ProN','Yu Mincho','Noto Serif JP',serif"
_SANS = "'Zen Kaku Gothic New','Hiragino Kaku Gothic ProN','Yu Gothic','Noto Sans JP',sans-serif"
_CONTACT = "contact@noshi.me"


def _due_phrase(days_left: int) -> str:
    """急かさない残日数の言い回し（frontend の daysLeftLabel とトーンを揃える）。"""
    if days_left <= 0:
        return "きょうがお返しの目安です"
    return f"あと{days_left}日でお返しの目安です"


def _yen(n: int) -> str:
    return f"¥{n:,}"


def render_reminder_email(reminders: list[DueReminder], today: datetime.date) -> tuple[str, str]:
    """リマインドメールの (件名, HTML本文) を返す。複数件は1通にまとめる。"""
    rows = ""
    for d in reminders:
        rows += f"""
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:12px;background:{_KINARI};border:1px solid {_BORDER_FAINT};border-radius:12px;">
                <tr><td style="padding:16px 18px;">
                  <div style="font-family:{_SANS};font-size:17px;font-weight:700;color:{_SUMI};">{_esc(d.party_name)} 様</div>
                  <div style="font-family:{_SANS};font-size:14px;color:{_SUMI_SUB};margin-top:4px;">{_esc(d.purpose)} ・ {_yen(d.amount)}</div>
                  <div style="font-family:{_SANS};font-size:14px;color:{_SHU};font-weight:700;margin-top:6px;">{_due_phrase(d.days_left)}</div>
                </td></tr>
              </table>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only">
<title>noshi お返しのリマインド</title>
</head>
<body style="margin:0;padding:0;background:{_KINARI};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_KINARI};">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" border="0" style="width:480px;max-width:100%;background:{_WASHI_RAISED};border:1px solid {_BORDER_FAINT};border-radius:16px;">
          <tr>
            <td style="padding:36px 28px 28px 28px;">

              <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
                <tr>
                  <td width="44" height="44" align="center" valign="middle" style="background:{_SHU};border-radius:50%;color:#ffffff;font-family:{_SERIF};font-size:23px;font-weight:700;line-height:44px;">の</td>
                  <td style="padding-left:10px;font-family:{_SERIF};font-size:26px;font-weight:700;color:{_SHU};letter-spacing:0.04em;">し</td>
                </tr>
              </table>

              <h1 style="margin:24px 0 0 0;text-align:center;font-family:{_SERIF};font-size:21px;font-weight:700;color:{_SUMI};letter-spacing:0.02em;">お返しの時期が近づいています</h1>
              <p style="margin:12px 0 0 0;text-align:center;font-family:{_SANS};font-size:15px;line-height:1.9;color:{_SUMI_SUB};">折を見て、お返しのご準備はいかがでしょう。</p>
              {rows}

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr><td style="padding:24px 0 0 0;border-top:1px solid {_BORDER_FAINT};"></td></tr>
              </table>
              <p style="margin:20px 0 0 0;text-align:center;font-family:{_SANS};font-size:12px;line-height:1.8;color:{_SUMI_MUTED};">
                noshi を開くと、お返しの目安額や品の候補をご案内します。<br>
                通知の停止はアプリのマイページから。お問い合わせ：<a href="mailto:{_CONTACT}" style="color:{_SUMI_SUB};text-decoration:underline;">{_CONTACT}</a>
              </p>

            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return SUBJECT, html


def _esc(s: str) -> str:
    """メール本文に差し込む相手名・用途の最小エスケープ。"""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- Lambda エントリポイント -------------------------------------------------


def handler(event: object, context: object) -> dict[str, object]:
    """EventBridge 日次トリガ。全世帯のお返しリマインドを送る。"""
    import os

    from .repository import DynamoRepository

    repo = DynamoRepository()
    from_email = os.environ["NOSHI_FROM_EMAIL"]
    today = datetime.date.today()
    sent = run_reminders(repo, today, _ses_sender(from_email))
    return {"sent": sent, "date": today.isoformat()}


def _ses_sender(from_email: str) -> SendFn:
    """SES でHTMLメールを送る送信関数を返す。"""
    import boto3

    ses = boto3.client("ses")

    def send(to: str, subject: str, html: str) -> None:
        ses.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html, "Charset": "UTF-8"}},
            },
        )

    return send
