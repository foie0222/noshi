# Functional Design — Validation Result (noshi-service)

**Re-validation attempt 3** (independent). Validates the builder's fix that added the `BR-SUG` business-rule group covering story S-6.

## Status: PASS

## Inputs validated

- Artifacts: `business-logic-model.md`, `domain-entities.md`, `business-rules.md`
- Answered questions: `functional-design-questions.md`
- Upstream (intent-001): `stories.md`, `component-methods.md`, `data-models.md`, `event-catalog.md`, `component-dependencies.md`, `cross-cutting.md`, `components.md`
- Note: `units-of-work.md` / `units-of-work-story-map.md` are not present in intent-001 because units-generation was collapsed (single MVP unit). The single-unit scope and full story ownership are declared explicitly in `business-logic-model.md` (Unit scope), satisfying Rule 2 in the collapsed-unit case.

## Scripts invoked

No `scripts/` directory exists for the `aidlc-functional-design` skill → no scripts. TOOLS: none.

## Spec rules checked (functional-design validation-spec)

| Rule | Result | Notes |
|---|---|---|
| 1 — three artifacts present & non-empty | PASS | All three present and substantive. |
| 2 — unit scope declared, all mapped stories appear | PASS | Unit `noshi-service`, stories S-1..S-14 listed, owning components listed. Collapsed single unit; scope declared in business-logic-model. |
| 3 — every mapped story addressed by ≥1 workflow | PASS | WF-1..WF-6 cover all stories. |
| 4 — component methods exist upstream | PASS | All referenced methods (suggest, select, calculate, override, submitJob, getJob, createRecord, setStatus, listPending, recordConsent, requestDeletion, exportData, generate, etc.) exist in `component-methods.md`. No invented methods. |
| 5 — domain events consistent with event-catalog | PASS | ExtractionRequested/Completed/Failed, SecurityEventRecorded match catalog. No new events introduced. |
| 6 — entities trace to upstream data-models, same owner | PASS | All 9 entities trace to data-models.md with same owning component. Refinement only (e.g., ExtractionJob adds needsReview[]) — additive refinement, not a new entity. |
| 7 — each entity has attributes, lifecycle, invariants | PASS | All 9 entities have attributes, lifecycle, and invariants. |
| 8 — complex-state entities have state machine | PASS | GiftEvent defines states (received/considering/done) with free-transition semantics and the done-exclusion invariant; consistent with answered Q3=b. |
| 9 — each BR has unique ID, type, trigger, logic, violation | PASS | All BR-* groups including BR-SUG-1..5 have unique IDs, soft/hard type, declarative logic, and violation/fallback behavior. |
| 10 — BR↔story both directions | PASS | Full bidirectional coverage confirmed (see matrix). S-6 now covered by BR-SUG. No orphan rules, no orphan stories. |
| 11 — no contradictory rules | PASS | BR-EVT-1 (free transition) vs BR-EVT-2 (done excluded from pending) are complementary, not contradictory. No conflicting outcomes for any shared trigger. |
| 12 — complex conditional logic uses decision table | PASS | BR-HR-1 (per-purpose return rates) expressed as a table. Other rules are single-condition. |
| 13 — business logic only, no tech specifics | PASS | No language/framework/DB/broker/vendor specifics. Ports (GiftCatalogPort, OcrLlmPort) are logical abstractions. |
| 14 — integration touchpoints reference declared dependencies | PASS | BR-SUG references GiftCatalogPort and GiftEvent linkage; both declared in `component-dependencies.md` (GiftSuggestion→GiftCatalogPort port; GiftSuggestion→GiftEvent sync). No undeclared cross-boundary interactions. |

## Rule 10 — full story → rule coverage matrix

**Reverse direction (every story covered by ≥1 BR):**

| Story | Covering business rule(s) | Covered |
|---|---|---|
| S-1 サインアップ/ログイン | BR-AUTH | ✓ |
| S-2 アカウント/データ削除 | BR-PRV | ✓ |
| S-3 画像から贈答を記録 | BR-EX, BR-VAL | ✓ |
| S-4 履歴の記録・閲覧・集計 | BR-RET | ✓ |
| S-5 推奨お返し額の算出 | BR-HR | ✓ |
| **S-6 お返し品の提案と紐付け** | **BR-SUG** | **✓ (newly covered — prior gap resolved)** |
| S-7 礼状文面の生成 | BR-LTR | ✓ |
| S-8 イベントのステータス管理 | BR-EVT, BR-RET | ✓ |
| S-9 AI 抽出サービスの挙動 | BR-EX, BR-VAL | ✓ |
| S-10 本人スコープの強制 | BR-VAL, BR-AUTH | ✓ |
| S-11 他人データ参照の拒否 | BR-AUTH | ✓ |
| S-12 認証の悪用防止 | BR-AUTH | ✓ |
| S-13 機微操作の監査証跡 | BR-AUTH | ✓ |
| S-14 利用目的・第三者PII同意 | BR-PRV | ✓ |

All 14 stories in unit scope are covered. **No orphan story.**

**Forward direction (every BR traces to a valid in-scope story):**

| Business rule | Stories field | Valid |
|---|---|---|
| BR-HR | S-5 | ✓ |
| BR-EX | S-3, S-9 | ✓ |
| BR-VAL | S-3, S-9, S-10 | ✓ |
| BR-AUTH | S-1, S-10, S-11, S-12, S-13 | ✓ |
| BR-EVT | S-8 | ✓ |
| BR-RET | S-4, S-8 | ✓ |
| BR-SUG | S-6 | ✓ |
| BR-LTR | S-7 | ✓ |
| BR-PRV | S-2, S-14 | ✓ |

Every BR references only valid S-1..S-14 stories. **No orphan rule.**

## BR-SUG fix verification (the change under re-validation)

The added `BR-SUG` group is well-formed and complete:
- **BR-SUG-1 (soft)** — candidate derivation from budget (half-return amount) / relationship / purpose. Maps to `GiftSuggestion.suggest(budgetRange, relationship, purpose)`. Satisfies S-6 AC1.
- **BR-SUG-2 (hard)** — proposal-only; each candidate = summary + external reference link; no in-app purchase/payment. Consistent with ReturnSuggestion entity invariant ("購入/決済情報は持たない"). Satisfies S-6 AC2.
- **BR-SUG-3 (hard)** — single selection links to target GiftEvent. Maps to `GiftSuggestion.select(userId, eventId, suggestionId)` and declared GiftSuggestion→GiftEvent sync dependency. Satisfies S-6 AC3.
- **BR-SUG-4 (soft)** — catalog-unavailable fallback ("候補なし" + defer return, flow continues). Consistent with WF-3 exception path and trust-boundary "failure fallback" in cross-cutting.
- **BR-SUG-5 (hard)** — catalog sends limited to non-PII (budget/purpose/relationship); restricted/name not sent. Consistent with cross-cutting minimization and OWASP A03 trust-boundary protection over GiftCatalogPort.

No regression: the four issues resolved in attempt 2 remain resolved (entity field classifications present, methods trace upstream, GiftEvent state model matches answered Q3=b, events match catalog). The single attempt-2 finding (S-6 reverse-coverage gap) is now closed.

## Lens rules checked — OWASP (functional-design stage applicable)

Applicable sections: **All Stages** (4 rules) + **application-design, functional-design, nfr-design, code-generation** (4 rules) = 8 rules → owasp:1..8.

| # | Rule | Result | Notes |
|---|---|---|---|
| 1 | No auth mechanism contradicting upstream auth model | PASS | BR-AUTH-1 enforces `resource.ownerId == session.userId` (single `owner` role), matching cross-cutting A01. No contradiction. |
| 2 | No plaintext credentials/secrets/restricted | PASS | authIdentifier/secretHash classified restricted; AuditEntry.metadata forbids plaintext restricted; BR-AUTH-2 / BR-LTR-1 / BR-SUG-5 enforce minimization. |
| 3 | Session/token least privilege + expiration/rotation | PASS | BR-AUTH-3 mandates rate limiting and session/token expiry & revocation (A07). |
| 4 | Security-relevant actions have audit coverage | PASS | BR-AUTH-2 logs authz failure / auth attempt / deletion / export to AuditLog; BR-PRV-2 audits deletion (A09). |
| 5 (stage) | Every data field has explicit classification | PASS | domain-entities.md classifies every field (restricted/confidential/internal). No unclassified data. |
| 6 (stage) | Trust-boundary crossings have validation/encoding strategy | PASS | BFF edge validation (BR-VAL); port sends minimized/masked (BR-LTR-1, BR-SUG-5). |
| 7 (stage) | External input surfaces have input validation | PASS | BR-VAL-1/2 validate image format/size and required fields; business-logic-model states all external input validated at BFF boundary. |
| 8 (stage) | Error handling does not leak sensitive info | PASS | BR-VAL-3 + cross-cutting: external errors are generic, internal detail logged only. |

## Findings

None. No spec-rule or lens-rule failures.

## Recommendations

None required. The artifacts pass all functional-design rules and all 8 applicable OWASP lens rules.

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: none
RULES: 1,2,3,4,5,6,7,8,9,10,11,12,13,14
LENS-RULES: owasp:1,2,3,4,5,6,7,8
---END-PROCESS-CHECK-DATA---
