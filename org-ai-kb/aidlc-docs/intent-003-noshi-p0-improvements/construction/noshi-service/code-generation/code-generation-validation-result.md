# Code Generation — Validation Result (intent-003 noshi-service, BROWNFIELD P0)

**Status:** PASS
**Validated:** 2026-06-06
**Unit:** noshi-service (code-generation stage)
**Active lens:** owasp (code-generation stage → All Stages 4 rules + application/functional/nfr-design/code-generation 4 rules = 8 rules)

The artifact under validation is the live repository (`backend/` + `frontend/`). Validation re-ran the test suites and inspected the changed source against the spec, upstream traceability docs, and the owasp lens.

---

## Test Evidence (re-run by validator)

| Command | Expected | Actual | Result |
|---|---|---|---|
| `cd backend && .venv/bin/python -m pytest -q` | 43 passed | **43 passed** in 0.93s | PASS |
| `cd frontend && npx vitest run` | 10 passed | **10 passed** (2 files) | PASS |
| `cd frontend && npx tsc --noEmit` | 0 errors | **0 errors** (exit 0) | PASS |

Backend new-functionality test coverage confirmed:
- `test_香典のお返し期限は四十九日後`, `test_出産祝いのお返し期限は一ヶ月後`, `test_中元歳暮はお返し期限を持たない`, `test_残日数を算出する` (rules.due_date / days_left).
- `test_あげた贈答はお返し対象に出ない` (given excluded from pending; ledger retained).
- `test_お返し不要の用途は未完了に出ない` (no-deadline excluded).
- `test_未完了ビューは期限と残日数を含む`, `test_未完了は期限の近い順に並ぶ` (due_at/days_left + ascending sort).
- `test_抽出モックが項目別の信頼度を返す` (per-field confidence, only party_name low).
Frontend: `daysLeftLabel` covered for >0 / 0 / <0 / null cases.

---

## Scripts Invoked

`.kiro/skills/aidlc-code-generation/scripts/` is absent → **no scripts**. (TOOLS: none.)

---

## Spec Compliance (code-generation validation-spec rules)

| Rule | Description | Result | Notes |
|---|---|---|---|
| 1 | No code before plan approved | PASS | code-generation-plan.md present; stage marked complete upstream. |
| 2 | Layer-by-layer; layer N+1 only after N compiles+tests pass | PASS | All tests green; brownfield改修 applied to existing layered structure (domain→ports→services→main; frontend lib→App). |
| 3 | ≤12 files/layer (prefer 5–8) | PASS | Changed set is small (6 backend, 3 frontend). |
| 4 | Unit tests in same layer as code | PASS | rules/services/ports/api tests + format.test.ts ship with the changed code. |
| 5 | Compile-fail self-correct ≤3; logic/test-fail stop | PASS | Final state compiles and all tests pass. |
| 6 | App code in workspace root, docs in aidlc-docs | PASS | Code under backend/frontend; CODE_SUMMARY + report under aidlc-docs. No mixing. |
| 7 | Brownfield: follow extracted conventions | PASS | New code matches existing style: dataclasses, `from __future__ import annotations`, Japanese docstrings tagging BR-* / FR / P0, pure functions in domain/rules.py, view-dict pattern in services. |
| 8 | Brownfield: no file modified without diff summary + approval | PASS | CODE_SUMMARY.md documents the per-file diff (rules/entities/ports/services/main, format.ts/App.tsx/styles.css); answered questions Q1/Q2 capture scope approval. |
| 9 | Every file traceable to a component + story | PASS | Changes map to FR-3-1..4 / BR-3-DUE/GIVEN/CONF and stories S3-1..S3-5 (see traceability below). |
| 10 | Re-invocation resumes from first unchecked layer | PASS (N/A) | Single completed generation; nothing to resume. |
| 11 | Layer checkpoint: files exist, build passes, tests pass | PASS | All changed files on disk; pytest/vitest/tsc green. |
| 12 | Implement cross-cutting patterns, don't invent | PASS | Reuses established patterns: ValidationError/ForbiddenError handlers, `_require_event` owner-scope, `_audit` (A09), generic error responses (A03). No new error/logging/validation pattern introduced. |

### Traceability (FR-3 / BR-3)
- **FR-3-1 / BR-3-DUE** → `rules.due_date` (香典+49 / 他+30 / 中元歳暮=None / occurred_at fallback), `rules.days_left`, `services._view` (due_at/days_left), `pending_views` (no-deadline excluded, ascending sort). 
- **FR-3-2** → `main.home` removed balance/diff, returns deadline-ordered pending; `App.tsx` home is deadline dashboard, SummaryBar removed from render.
- **FR-3-3 / BR-3-CONF** → `ports.OcrLlmMock.field_confidence` (party_name 0.58 low, others high), `services.field_review`, `main.capture` returns field_review; `App.tsx` review shows ✓確定 for high-confidence, 要確認 badge + warn frame only for low, "◯か所だけ確認".
- **FR-3-4 / BR-3-GIVEN** → `services.create_record` creates event only when `direction == "received"`; given retained in ledger.

---

## Lens Compliance — owasp (8 rules)

### All Stages (1–4)
| # | Rule | Result | Evidence |
|---|---|---|---|
| 1 | No auth/authz contradiction | PASS | Owner-scope unchanged: `services._require_event`, repository `get_*`/`list_*` filter by `user_id`; stub auth (X-User-Id → 401) intact in `main.current_user`. given-exclusion is a business filter on already-owner-scoped data; it does not bypass auth. |
| 2 | No plaintext secrets/restricted data | PASS | No secrets in changed code (grep clean). Audit `target_ref` stores identifiers only; restricted fields not logged. |
| 3 | Session/token least-privilege + expiration | PASS (N/A) | No session/token/credential handling introduced or modified by the diff. |
| 4 | Audit coverage for security events | PASS | `_audit` retained for `delete_record`, `authz_denied` (in `_require_event`). Diff does not remove any audit call. |

### application-design, functional-design, nfr-design, code-generation (5–8)
| # | Rule | Result | Evidence |
|---|---|---|---|
| 5 | Every data field classified | PASS | `ExtractionJob.field_confidence` is internal (per-field confidence floats), `candidates` already classified confidential; entities carry classification comments (restricted/confidential/internal). due_at/days_left are derived internal metadata. No unclassified field introduced. |
| 6 | Trust-boundary crossings have validation/encoding | PASS | API→service boundary unchanged; `create_record` still runs `validate_record`; LLM/catalog ports send minimized data (letter generation passes no restricted PII). |
| 7 | External inputs validated | PASS | `/api/records` uses Pydantic `RecordIn` + `validate_record`; `/api/home` and `/api/capture` take no external body beyond auth header; `half-return` keeps amount>0 guard. |
| 8 | Error handling doesn't leak internals | PASS | `home` returns only pending views + recent records (no balance/internal diff that was previously exposed); `capture` returns candidates/confidence/field_review/needs_review — no stack traces/paths. ForbiddenError→`{"detail":"forbidden"}`, ValidationError→field messages; generic-error test passes. |

**given-exclusion consistency:** Confirmed consistent — given creates no event (`create_record` guards on `received`), and `pending_views` independently excludes given (no event exists) and no-deadline purposes (`due_at is None` filter). Two independent layers, both tested.

---

## Findings

None. No spec-rule or owasp-lens failures.

## Recommendations

- Non-blocking (already noted in CODE_SUMMARY as known debt): `SummaryBar` component is now unused after balance removal but still imported/tested; its `SummaryBar.test.tsx` is one of the 10 passing frontend tests. Consider removing the component and its test in a follow-up intent to avoid dead code. Not a validation failure.

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: none
RULES: 1,2,3,4,5,6,7,8,9,10,11,12
LENS-RULES: owasp:1,2,3,4,5,6,7,8
---END-PROCESS-CHECK-DATA---
