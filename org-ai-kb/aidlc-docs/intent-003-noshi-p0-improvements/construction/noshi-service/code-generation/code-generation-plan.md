# Code Generation — Plan（intent-003 / TDD 改修）

## backend
- [x] rules.py: due_date(occurred_at, purpose)→date|None、days_left(due, today)。期限ルール（BR-3-DUE）＋テスト
- [x] services.py: create_record は received のみイベント生成（BR-3-GIVEN）＋テスト
- [x] services.py: pending_views に due_at/days_left、期限なし除外、残日数昇順ソート＋テスト
- [x] ports.py: OcrLlmMock を per-field 信頼度（一部のみ低信頼）に。needs_review 判定＋テスト
- [x] main.py: /api/home から収支差分を撤去、pending を期限つき・昇順で返す

## frontend
- [x] format.ts: daysLeftLabel(days)→「のこり◯日／期限超過」＋vitest
- [x] App.tsx home: SummaryBar 撤去、期限つきカード（残日数バッジ・昇順）
- [x] App.tsx review: 高信頼=確定済み表示、低信頼のみ強調

## 検証
- [x] backend pytest 全緑 / frontend vitest 全緑・tsc・build
