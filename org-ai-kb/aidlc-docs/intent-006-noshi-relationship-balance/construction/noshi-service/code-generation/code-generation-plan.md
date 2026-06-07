# Code Generation — Plan（intent-006 / TDD）
## backend
- [x] rules.py: relationship_balance(records, today)→[{party_name,received,given,diff,last_at,status,attention}]（BR-6-BALANCE）＋テスト
- [x] services.py: relationships(user_id)＋テスト
- [x] main.py: GET /api/relationships
## frontend
- [x] App.tsx: マイページに「おつきあい」一覧（status バッジ・気になる関係を上位/控えめ）
- [x] styles.css: balance バッジ
## 検証
- [x] backend pytest 緑 / frontend vitest・tsc・build 緑
