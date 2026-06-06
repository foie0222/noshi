# NFR Assessment — Validation Result (noshi-service)

**Validator:** AI-DLC validator sub-agent
**Stage:** nfr-assessment
**Date:** 2026-06-05
**Re-validation attempt:** 2 (after builder fix for attempt-1 failures on Rule 9 and Rule 3)
**Artifacts validated:**
- `nfr-requirements.md`
- `tech-stack-decisions.md`

**Status:** PASS

---

## Scripts invoked

The skill scripts directory `.kiro/skills/aidlc-nfr-assessment/scripts/` does not exist. No scripts were run.

- TOOLS: none

---

## Spec compliance (aidlc-nfr-assessment validation-spec)

| Rule | Description | Result |
|---|---|---|
| 1 | Both artifacts present and non-empty | PASS |
| 2 | nfr-requirements declares unit scope (name, owning components, complexity summary) | PASS |
| 3 | Every relevant requirements.md NFR addressed or flagged with reason | PASS |
| 4 | Performance reqs reference specific business-logic-model workflows; no invented ops | PASS |
| 5 | Reliability addresses dependency failure for every integration touchpoint | PASS |
| 6 | Security addresses data classification for every domain entity | PASS |
| 7 | Observability extends (not contradicts) cross-cutting logging taxonomy | PASS |
| 8 | Every NFR requirement has traceability reference to requirements.md IDs | PASS |
| 9 | Every tech stack decision has unique TSD-<n> ID, category, choice, alternatives, rationale referencing NFR reqs, documented trade-offs | PASS |
| 10 | Tech stack decisions do not contradict each other; tensions documented with resolution | PASS |
| 11 | Tech stack decisions do not contradict cross-cutting constraints/standards | PASS |

### Notes on passing rules

- **Rule 2:** Unit scope declared (lines 4–6): unit `noshi-service`, owning components (Identity … BFF), functional-complexity summary (中, async generative-AI/OCR, single user/data boundary).
- **Rule 4:** NFR-P1→WF-4 (台帳閲覧・集計), NFR-P2→WF-2 (抽出). Both workflows exist in `business-logic-model.md`. NFR-P3 (sync APIs: half-return / ledger search) maps to real operations in WF-3/WF-4. No invented operations.
- **Rule 5:** Integration touchpoints in `business-logic-model.md` are the external ports (OcrLlmPort, GiftCatalogPort) and IdP. NFR-R1 covers fallback for all three (手入力 / 候補なし / メールログイン); NFR-R2 covers SQS retry + DLQ + jobId idempotency.
- **Rule 6:** NFR-SE1 classifies all `domain-entities.md` entities across restricted (User authIdentifier/secretHash), confidential (Party/GiftRecord/Letter PII & amounts), internal (ConsentRecord, GiftEvent, ReturnSuggestion, ExtractionJob status, AuditEntry). All entities covered.
- **Rule 7:** NFR-O2 explicitly reuses the cross-cutting taxonomy `auth/authz/data/extraction/system` and extends it with traces/correlation IDs — no contradiction.
- **Rule 10:** The DynamoDB-vs-ad-hoc-query tension (NoSQL vs ledger search/aggregation in NFR-P3/WF-4) is documented in TSD-3 with an access-pattern-driven resolution (GSIs for party/status, design-time pattern fixing, pre-computed aggregates). No latency conflict. TSD-2 SPA-bundle-vs-NFR-P1 tension and TSD-4 fully-async-vs-UX tension are also documented with resolutions.
- **Rule 11:** Decisions reinforce cross-cutting standards: owner-scope (A01) enforced at the DynamoDB key level (PK contains userId), BFF input validation (A03), audit (A09), generic error format. No contradiction.

---

## Lens compliance — owasp (ACTIVE)

Stage `nfr-assessment` is not listed in any stage-specific owasp section, so only **### All Stages** (4 rules) applies.

| Rule | Description | Result |
|---|---|---|
| 1 | No auth/authz mechanism contradicting cross-cutting / lens answers | PASS |
| 2 | No plaintext storage/log/transmit of credentials/secrets/restricted | PASS |
| 3 | Session/token/credential handling uses least privilege + expiry/rotation | PASS |
| 4 | Security-relevant actions have logging/audit coverage | PASS |

### Notes

- **owasp-1:** TSD-7 (OIDC + email, token revocation/expiry/rate-limit) and PK-embedded owner-scope (A01) are consistent with the cross-cutting auth model (single role `owner`, owner-scope enforcement, defense in depth). No contradiction.
- **owasp-2:** NFR-SE2 mandates encryption at rest (KMS) and in transit (TLS 1.2+); NFR-SE6 forbids plaintext restricted; AuditEntry metadata forbids plaintext restricted; ExtractionJob.candidates expire via TTL.
- **owasp-3:** TSD-7 defines token expiry + revocation + auth rate-limiting; S3 signed URLs are short-lived (TSD-5); least privilege via owner-scope keys.
- **owasp-4:** NFR-SE6 + NFR-O1/O3 cover audit of auth/authz failures, deletion, and export into AuditLog, with alerting on authz-failure spikes.

---

## Re-verification of attempt-1 failures

### Rule 9 (attempt-1 FAIL) — now PASS
- **ID format fixed.** All decisions now use the prescribed `TSD-<n>` scheme (TSD-1 … TSD-8), each unique. The prior `TS-<n>` naming is gone from the preamble (line 3) and every section heading.
- **Trade-offs added.** Each decision now carries an explicit `トレードオフ:` line: TSD-1 (L9), TSD-2 (L16), TSD-3 (L31), TSD-4 (L36), TSD-5 (L43), TSD-6 (L50), TSD-7 (L56), TSD-8 (L63). Each states the accepted cost/limitation of the chosen option (e.g., TSD-1 dual language/type maintenance mitigated by OpenAPI gen; TSD-3 no ad-hoc queries mitigated by design-time access patterns).
- **Rationale tied to specific NFR IDs.** Each decision adds a `関連NFR:` line referencing concrete NFR identifiers: TSD-1→NFR-P2/P3, NFR-SE5, NFR-S1; TSD-2→NFR-4, NFR-P1; TSD-3→NFR-S3/A2/D1/D2/SE3; TSD-4→NFR-R2/S2/A3/P2; TSD-5→NFR-SE2/P1/P2/A2; TSD-6→NFR-R1/SE5/P2; TSD-7→NFR-SE4; TSD-8→dev-productivity/NFR-A. Category, choice, and rejected alternatives (`代替（却下）`) present in each.

### Rule 3 (attempt-1 FAIL on NFR-4) — now PASS
- A new section **"Usability / Accessibility（→ NFR-4）"** (nfr-requirements.md L42–46) addresses NFR-4: NFR-U1 mobile-first responsive (375px baseline, one-hand/3-tap), NFR-U2 WCAG 2.1 AA (4.5:1 contrast, form labels, visible focus, alt text, error color+text), NFR-U3 single-language JP UI / PWA outlook, plus a realization note (TSD-2 code-splitting for first paint).
- All requirements.md NFRs NFR-1..NFR-5 are now addressed: NFR-1→Performance, NFR-2→Security+Observability, NFR-3→Availability+Scalability, **NFR-4→Usability/Accessibility (new)**, NFR-5→NFR-SE7(APPI)+Data.
- Traceability line (L54) now includes **NFR-U* → NFR-4** alongside all other prefixes — no NFR left untraced.

---

## Findings (failures)

None. No regressions detected — all rules that passed in attempt 1 remain satisfied, and the two attempt-1 failures (Rule 9, Rule 3) are now resolved.

---

## Recommendations

1. (Non-blocking) NFR-P3 (sync API p95 < 500ms) does not cite a specific WF id; it is a cross-cutting sync-API target rather than an invented operation, so Rule 4 still passes. Optionally tie it to WF-3/WF-4 sync paths for tighter traceability in a future revision.

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: none
RULES: 1,2,3,4,5,6,7,8,9,10,11
LENS-RULES: owasp:1,2,3,4
---END-PROCESS-CHECK-DATA---
