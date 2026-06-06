# Requirements Analysis — Validation Result (intent-003 noshi P0 improvements)

**Status:** pass

Validated artifact: `requirements.md` against the requirements-analysis validation-spec and the active OWASP lens (stage = requirements-analysis).

---

## Rules checked (requirements-analysis validation-spec)

| Rule | Description | Result |
|---|---|---|
| 1 | All 5 sections present (Intent summary / Functional / Non-functional / Assumptions / Out of scope) | PASS |
| 2 | Every human-intent capability traceable to ≥1 FR/NFR | PASS |
| 3 | FRs numbered (FR-<n>) and verifiable pass/fail | PASS |
| 4 | NFRs include measurable criteria | PASS |
| 5 | Assumptions explicitly flagged as assumptions | PASS |

### Rule 1 — Sections
All five required sections present: "Intent summary", "Functional requirements（新規・変更）", "Non-functional requirements", "Assumptions", "Out of scope（本 intent では除外）". No empty sections. Confirmed structurally by `verify-structure.sh` (exit 0).

### Rule 2 — Traceability / coverage
Every P0 capability from `intent.md` and `ux-product-review-001.md` is covered:
- P0-1 お返し期限ダッシュボード → FR-3-1 (標準期限・残日数・期限順ソート・超過強調) + FR-3-2 (ホーム主役化).
- P0-2 撮影の要所だけ確認 → FR-3-3 (高信頼=確定済み / 低信頼のみ強調 / 強制レビュー撤廃).
- P0-3 収支フレーミング見直し → FR-3-2.2 (収支・差分の撤去).
- 負債#1 given 除外 → FR-3-4 (given は pending を作らない / 台帳には残る).
Upstream intent-001 FR/NFR are explicitly retained (NFR section + intent summary 源泉), so the brownfield baseline is preserved.

### Rule 3 — FR numbering / verifiability
FRs use a consistent `FR-3-<n>` hierarchy (FR-3-1 … FR-3-4) with verifiable leaf items (e.g., FR-3-1.1 deterministic deadline formulae, FR-3-4.1 "given creates no pending event"). All are pass/fail testable.

### Rule 4 — NFR measurability
NFRs inherit measurable criteria from intent-001/002 (本人スコープ A01, 入力検証 A03, 監査 A09, restricted 非ログ, 外部送信最小化, p95 perf, WCAG AA). New NFR content is quantified/deterministic: deadline calculation is deterministic, timezone = Japan, date-based; data classification/storage explicitly unchanged by the diff removal.

### Rule 5 — Assumptions flagged
Assumptions are under an explicit "Assumptions" heading and framed as premises (stack unchanged, push out of scope = 画面表示のみ, 基準日 = occurred_at with 作成日 fallback). Not stated as facts.

---

## Lens rules checked — OWASP (stage = requirements-analysis)

Applicable sections: **All Stages** (rules 1–4) + **requirements-analysis, user-stories** (rules 5–6).

| Lens rule | Description | Result |
|---|---|---|
| owasp:1 | No auth/authz mechanism contradicting upstream model | PASS |
| owasp:2 | No plaintext credentials/secrets/restricted data | PASS |
| owasp:3 | Session/token/credential least privilege + expiry/rotation | PASS |
| owasp:4 | Security-relevant actions have audit/logging coverage | PASS |
| owasp:5 | Security-implicated capabilities traceable to security req | PASS |
| owasp:6 | Sensitive data types identified with high-level classification | PASS |

- owasp:1 — NFR section explicitly keeps 本人スコープ (A01) from intent-001; no new or contradicting auth model is introduced. PASS.
- owasp:2 — restricted 非ログ is stated unchanged; no plaintext credential/secret flow introduced. PASS.
- owasp:3 — No new session/token/credential storage introduced; intent-001 policies inherited unchanged. PASS.
- owasp:4 — 監査 (A09) coverage explicitly retained as 不変. PASS.
- owasp:5 — This brownfield change introduces no new security capability; the owner-scope (A01) / 入力検証 (A03) / audit security requirements from intent-001 are carried forward and traceable. PASS.
- owasp:6 — Sensitive data classification is acknowledged: NFR states 「差分撤去でデータ分類・保存は不変」, preserving the confidential〜restricted classification and APPI compliance established in intent-001. The removal of the balance diff (FR-3-2.2) does not alter stored data or its classification. PASS.

---

## Scripts invoked

| Script | Exit code | Output |
|---|---|---|
| `verify-structure.sh` | 0 | STRUCTURAL VALIDATION PASSED — All 5 required sections present; Functional requirements use FR-<n> numbering |

---

## Clarification consistency

Cross-checked `requirements.md` against the answered `requirements-analysis-questions.md`:

- Q1 [a] standard deadlines → FR-3-1.1 reproduces the table exactly (香典 +49日, 出産/結婚/快気/一般慶事 +1ヶ月, お中元・お歳暮 期限なし). Consistent.
- Q2 [a] capture = confirm-only, batch deferred → FR-3-3 + Out-of-scope まとめ撮り. Consistent.
- Q3 [b] REMOVE balance diff entirely → FR-3-2.2 撤去 of 収支（もらった/あげた/差分）. Consistent (note: the answer overrides the recommendation a; requirements correctly follow the chosen answer b).
- Q4 [a] given excluded from pending, ledger retained → FR-3-4.1/FR-3-4.2. Consistent.
- Q5 scope = P0-1/2/3 + given除外; P1/P2 deferred; stack unchanged → Out-of-scope + Assumptions. Consistent.

No inconsistencies found.

---

## Findings

None. All spec rules, all applicable OWASP lens rules, the deterministic script, and clarification consistency pass.

## Recommendations

- (Optional, non-blocking) FR-3-1.4 marks 上書き as 将来拡張可 while still listed as an FR; downstream stories may want to explicitly tag it as deferred-within-FR to avoid scope ambiguity. Not a spec violation.

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: verify-structure.sh
RULES: 1,2,3,4,5
LENS-RULES: owasp:1,2,3,4,5,6
---END-PROCESS-CHECK-DATA---
