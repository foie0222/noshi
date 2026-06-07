# Intent — noshi record given (bugfix + feature)

## Prompt
「あげた(贈与)」贈答を UI から記録できるようにし、given 時に create_record が 500 になるバグを修正したい。brownfield・TDD。

## Summary
現状 UI（撮影フロー）は direction=received 固定で、「あげた(贈与)」を記録できない。また API は given レコード作成時に create_record が None イベントを vars() して 500 になる不具合がある。本 intent では (1) given 時にイベントを作らず正しく 200 を返すよう修正、(2) 記録確認画面に 受領/贈与 の選択を追加し「あげた」を記録できるようにする。bug fix + 小機能。stack 不変・TDD。

## Slug
noshi-record-given

## Type
bug fix（＋小機能）

## Upstream
- intent-001..007 の成果物と実コード（特に intent-003 given除外, intent-002 create_record/main）
