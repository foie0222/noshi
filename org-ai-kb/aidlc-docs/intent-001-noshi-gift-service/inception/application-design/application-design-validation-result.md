# Application Design — Validation Result

**Stage:** application-design
**Status:** PASS
**Validated:** 2026-06-04
**Active lens:** owasp

---

## 1. Scope

Artifacts validated:
- components.md, component-methods.md, component-dependencies.md, services.md, cross-cutting.md (always-on)
- data-models.md, api-contracts.md, event-catalog.md, external-dependencies.md (conditional, present)

Answered questions: application-design-questions.md
Upstream (traceability): requirements-analysis/requirements.md, user-stories/stories.md, user-stories/personas.md, wireframes/screen-data-map.md

Scripts: `.kiro/skills/aidlc-application-design/scripts/` is ABSENT → TOOLS: none.

---

## 2. Spec Rules (application-design validation-spec)

| Rule | Description | Result |
|---|---|---|
| 1 | All four always-on artifacts + cross-cutting.md present & non-empty | PASS |
| 2 | Conditional artifacts present when applicable | PASS |
| 3 | Every component in components.md appears in component-methods.md (≥1 method) and component-dependencies.md | PASS |
| 4 | Every service references ≥1 component | PASS |
| 5 | Every story addressable by a service/component/API/event | PASS |
| 6 | Every entity has exactly one owning component; no shared ownership | PASS |
| 7 | Every API uses the cross-cutting error format | PASS |
| 8 | Every event has ≥1 producer and ≥1 consumer | PASS |
| 9 | Every external dependency has ≥1 consumer | PASS |
| 10 | All artifacts logical — no tech/vendor specifics | PASS (see note) |
| 11 | Circular dependencies listed with justification | PASS |
| 12 | screen-data-map fields servable by the design | PASS |

### Rule detail / evidence

- **Rule 1:** All five required files present and non-empty.
- **Rule 2:** Persistence exists → data-models.md present. APIs exposed (BFF) → api-contracts.md present. Event-driven (extraction/audit) → event-catalog.md present. External integrations (OCR/LLM, catalog, IdP) → external-dependencies.md present. All four conditionals correctly produced; no omission to justify.
- **Rule 3:** 10 components (Identity, ConsentPrivacy, GiftLedger, Extraction, HalfReturnCalculator, GiftSuggestion, LetterGenerator, GiftEvent, AuditLog, BFF). Each has ≥1 method in component-methods.md and appears in the component-dependencies.md matrix.
- **Rule 4:** All 6 services list components used; every referenced component exists in components.md.
- **Rule 5:** Stories S-1…S-14 all addressed. Mapping: S-1/S-12/S-14 (Onboarding), S-3/S-9 (CaptureRecord), S-4 (Ledger), S-5/S-6/S-7/S-8 (Return), S-2/S-14 (Privacy), S-10/S-11/S-13 (AccessControl). No unmapped story.
- **Rule 6:** Owners — User→Identity, ConsentRecord→ConsentPrivacy, Party→GiftLedger, GiftRecord→GiftLedger, ExtractionJob→Extraction, GiftEvent→GiftEvent, ReturnSuggestion→GiftSuggestion, Letter→LetterGenerator, AuditEntry→AuditLog. Each entity has exactly one owner; no two components share an entity. (Session is owned by Identity per components.md but is not a data-models entity, so out of Rule 6 scope.)
- **Rule 7:** All API errors draw from the cross-cutting code set (UNAUTHENTICATED, FORBIDDEN, VALIDATION_FAILED, RATE_LIMITED, EXTRACTION_FAILED, NOT_FOUND, CONFLICT, INTERNAL). Generic client messaging is mandated.
- **Rule 8:** ExtractionRequested (P: Extraction / C: extraction worker), ExtractionCompleted (P: Extraction / C: BFF, GiftLedger), ExtractionFailed (P: Extraction / C: BFF), SecurityEventRecorded (P: Identity/ConsentPrivacy/GiftLedger / C: AuditLog). All have producer + consumer.
- **Rule 9:** OcrLlmPort→Extraction, LetterGenerator; GiftCatalogPort→GiftSuggestion; IdentityProviderPort→Identity. All have consumers.
- **Rule 10:** Artifacts stay logical (logical types, ports, deferral of broker/SDK/endpoints to construction). NOTE: external-dependencies.md names "OAuth2/OIDC" for IdentityProviderPort. This is a widely-used auth-protocol family reference, not a vendor/SDK lock-in, and concrete details are explicitly deferred to construction; treated as an acceptable integration-type label, not a violation. Flagged as a minor observation only.
- **Rule 11:** component-dependencies.md "循環依存" section explicitly states none, with justification (Extraction↔GiftLedger split into event vs. reference; HalfReturn/Suggestion/Letter→GiftEvent are write-direction only with no reverse dependency).
- **Rule 12:** All screen-data-map screens (login, consent, home, capture, extract-review, half-return, gift-suggest, letter, ledger, event-detail, settings, etc.) map to BFF APIs / components. Summary/pending/recent served by home.get; extraction candidates by capture.jobStatus; ledger fields by ledger.search; etc. No unservable screen data need.

---

## 3. OWASP Lens Rules (stage = application-design)

Applicable sections: "### All Stages" (4 rules) + "### application-design, functional-design, nfr-design, code-generation" (4 rules) = 8 rules, numbered 1–8.

| Rule | Section / Description | Result |
|---|---|---|
| 1 | All Stages: no auth model contradiction vs. upstream/lens answers | PASS |
| 2 | All Stages: no plaintext credentials/secrets/restricted in store/log/transmit | PASS |
| 3 | All Stages: session/token/credential handling = least privilege + expiry/rotation | PASS |
| 4 | All Stages: security-relevant actions have audit coverage | PASS |
| 5 | app-design: every data field/flow has explicit classification | PASS |
| 6 | app-design: every trust boundary crossing has validation/encoding strategy | PASS |
| 7 | app-design: every external input surface has input validation | PASS |
| 8 | app-design: error handling does not leak sensitive info | PASS |

### Lens evidence

- **[owasp] Rule 1:** cross-cutting.md authorization model (single `owner` role, owner-scope `resource.ownerId == session.userId`) is consistent with upstream stories S-10/S-11/S-12 and the OWASP lens intent. Identity component centralizes auth; no contradicting mechanism introduced.
- **[owasp] Rule 2:** data-models.md marks authIdentifier/secretHash as restricted; AuditEntry metadata and event payloads explicitly forbid plaintext restricted (identifier/hash/mask references). External-port sends are minimized/masked. No plaintext credential/secret flow.
- **[owasp] Rule 3:** Identity issues/revokes sessions/tokens; cross-cutting + S-12 define expiration and revocation; single least-privilege `owner` role. revokeExpired() present.
- **[owasp] Rule 4:** AuditLog component + SecurityEventRecorded event cover auth attempts, authz failures, deletion, export. cross-cutting "ログ分類" enumerates auth/authz/data categories. No security event lacking audit coverage.
- **[owasp] Rule 5:** Every field in data-models.md carries a classification (restricted/confidential/internal). cross-cutting "データ分類" defines the baseline. No unclassified data field/flow.
- **[owasp] Rule 6:** cross-cutting "トラスト境界" documents three boundaries (external→BFF untrusted with validation/authN/authZ; BFF→internal trusted-but-verified with scope propagation; component→external port untrusted with minimization/fallback). Each crossing has a validation/encoding/minimization strategy.
- **[owasp] Rule 7:** External input surfaces (BFF APIs, capture image upload, form fields) have documented validation: cross-cutting edge validation (format/type/size/required/allowed values, reject-by-default) plus per-component business preconditions. capture.submit validates format/size; ledger.createRecord validates fields.
- **[owasp] Rule 8:** cross-cutting error format mandates generic client messages without stack traces/internal paths/schema/credentials; INTERNAL details stay in logs only. ExtractionFailed exposes only a generic client error with internal reasonCode kept in logs. extract-error screen shows generic message. No info leak.

---

## 4. Clarification Consistency (application-design-questions.md)

- **Q1 = (a) capability/domain logical components:** Reflected — components.md defines capability/domain components (Identity, GiftLedger, Extraction, HalfReturnCalculator, GiftSuggestion, LetterGenerator, GiftEvent, ConsentPrivacy, AuditLog) as a modular single service. CONSISTENT.
- **Q2 = (a) extraction async via job + events:** Reflected — only Extraction is asynchronous (ExtractionRequested/Completed/Failed); event-catalog.md present; sync flows (half-return/suggest/letter/ledger) explicitly not eventized. CONSISTENT.
- **Q3 = (a) BFF aggregation:** Reflected — BFF component + api-contracts.md BFF-exposed APIs; BFF is the trust boundary and authorization front line. CONSISTENT.
- **Q4 = (a) internal port isolation for OCR/LLM:** Reflected — OcrLlmPort/GiftCatalogPort/IdentityProviderPort internal ports with failure modes in external-dependencies.md. CONSISTENT.

---

## 5. Completeness

- Story/requirement coverage at component level: all 14 stories trace to services/components; system + security/abuse stories (S-9..S-13) covered by Extraction, AccessControlService, AuditLog. No coverage gap.
- screen-data-map source-component estimates resolve cleanly to final components (e.g., AuthService→Identity, LedgerService→GiftLedger, EventService→GiftEvent, SuggestionService→GiftSuggestion). No orphan screen.
- No logical inconsistency found between data-models, api-contracts, event-catalog, and dependencies.

---

## 6. Findings

No failures.

Minor observations (non-blocking, do not affect status):
- external-dependencies.md references "OAuth2/OIDC" for IdentityProviderPort. Acceptable as an integration-type label with concrete details deferred to construction. Consider stating the protocol reference as an example only if strict technology-neutrality is desired.

## 7. Recommendations

- None required for PASS. Optional: in a future stage, make the IdentityProviderPort note explicitly "protocol family (example)" to keep inception fully technology-neutral.

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: none
RULES: 1,2,3,4,5,6,7,8,9,10,11,12
LENS-RULES: owasp:1,2,3,4,5,6,7,8
---END-PROCESS-CHECK-DATA---
