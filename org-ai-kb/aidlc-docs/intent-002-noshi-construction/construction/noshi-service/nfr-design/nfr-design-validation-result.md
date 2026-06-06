# NFR Design — Validation Result (noshi-service)

**Status:** PASS
**Attempt:** 2 (re-validation)
**Validated artifacts:** `nfr-design-patterns.md`, `logical-components.md`
**Answered questions:** `nfr-design-questions.md`
**Scripts invoked:** none (skill has no `scripts/` directory)

This re-validation was performed independently. Particular attention was paid to the four items that failed attempt 1 (Rules 5, 7, 8, 9).

## Spec Rules (aidlc-nfr-design)

| Rule | Result | Notes |
|---|---|---|
| 1 Both artifacts present & non-empty | PASS | Both files present with substantive content. |
| 2 NFRs implying patterns/components addressed | PASS | NFR-P1/P2/P3, S2, A1–A3, SE1–SE7, R1–R3, O1–O3 each map to a pattern or logical component. NFR-U* (WCAG/responsive) and NFR-D3 (residency) imply no resilience/infra pattern at this stage; P1 first-paint is covered by P-PERF-3. No unaddressed pattern-implying NFR. |
| 3 Patterns reference a specific NFR ID | PASS | Every pattern group carries a `(→ NFR-*)` / OWASP traceability header. |
| 4 Patterns applied to real components/touchpoints | PASS | Application points (OcrLlmPort/GiftCatalogPort/IdP, BFF, Extraction, ObjectStore, data store) trace to upstream `components.md` and `business-logic-model.md`. No invented points. |
| 5 Same-component pattern interaction & ordering | PASS (was FAIL attempt 1) | P-RES now states explicit nesting **Fallback ▷ CircuitBreaker ▷ Retry ▷ Timeout**, with breaker counting retry-inclusive attempts as one event. Resolved. |
| 6 Logical components positioned in topology | PASS | Every LC-1..LC-7 has a 配置 line referencing upstream components/ports. |
| 7 Every logical component specifies a failure mode | PASS (was FAIL attempt 1) | All LC-1..LC-7 now carry a 失敗モード line. Resolved. |
| 8 Config defaults derived from NFR targets w/ rationale | PASS (was FAIL attempt 1) | Concrete defaults present with derivation: timeout 3s (vs p95<500ms NFR-P3), retry max 3 / backoff 200ms×2^n cap 2s, visibility 60s (vs NFR-P2 p95<10s), max-receive 3→DLQ, breaker 50%/20 + 30s half-open, autoscale depth>100, token 15m/14d, auth lockout 5/min, image ≤10MB JPEG/PNG/HEIC, signed-URL TTL 5m, RPO≤24h, error budget <5%. Resolved. |
| 9 Logical-only, no vendor/cloud/infra names | PASS (was FAIL attempt 1) | Grep for SQS, S3, DynamoDB, KMS, CloudWatch, Lambda, AWS, Cognito, Aurora, RDS, SNS, GSI, pydantic, React, Fargate, ECS/EKS, API Gateway, CloudFront, ap-northeast, Azure, GCP returned ZERO matches in both artifacts. Logical terms used throughout (JobQueue, ObjectStore, KeyManagement, 鍵管理サービス, 二次インデックス). Resolved. (Note: vendor names appear only in `nfr-design-questions.md` recommendations, which is not a validated artifact.) |
| 10 No contradiction with cross-cutting standards | PASS | deny-by-default authz, owner-scope enforcement, audit logging, generic external error messages, edge input validation, restricted-no-plaintext all consistent with `cross-cutting.md`; design extends, does not contradict. |
| 11 No over-engineering beyond NFR traceability | PASS | Every pattern/component traces to an NFR requirement; no unjustified additions. |

## Lens Rules (owasp — nfr-design stage)

Applicable sections: **All Stages** (1–4) + **application-design, functional-design, nfr-design, code-generation** (1–4). Reported sequentially as owasp:1–8.

| # | Rule | Result | Notes |
|---|---|---|---|
| 1 | Auth model not contradicted | PASS | P-SEC-2/3, LC-4 consistent with OIDC + single `owner` scope model. |
| 2 | No plaintext credentials/restricted data | PASS | P-SEC-1 encryption at rest/in transit; restricted plaintext storage/logging forbidden (A02). |
| 3 | Least privilege + expiration/rotation | PASS | Token lifetimes (15m/14d), key rotation (LC-7), auth rate limiting defined. |
| 4 | Security events audited | PASS | P-SEC-5 + LC-5 AuditSink append-only audit of security events (A09). |
| 5 | Data flows/fields classified | PASS | restricted/confidential/internal classification referenced from upstream; P-SEC-1 keys encryption off classification. |
| 6 | Trust boundary validation/encoding | PASS | P-SEC-4 edge + schema validation at BFF boundary; minimization before external port. |
| 7 | External input surfaces validated | PASS | P-SEC-4 schema + image format/size (≤10MB, JPEG/PNG/HEIC); signed-URL direct upload bounded. |
| 8 | Error handling no sensitive leak | PASS | LC-3/LC-4 return generic errors hiding internal info; fail-secure (P-SEC-6). |

## Clarification Consistency

Artifacts are consistent with the recorded answers (Q1 resilience, Q2 async, Q3 performance, Q4 security, Q5 observability). The Q&A file references vendor names in its *recommendation* lines, but the validated artifacts correctly abstract these to logical terms — no inconsistency, and Rule 9 applies to artifacts only.

## Completeness

No gaps found. All four previously-failing items are confirmed resolved and nothing regressed: ordering note present, failure modes on all seven components, NFR-derived defaults with rationale throughout, and a clean vendor-name scan (zero hits).

## Findings

None.

## Recommendations

None required for pass. Optional (non-blocking): NFR-U* accessibility targets and NFR-D3 data residency could be explicitly noted as deferred to frontend/infrastructure stages for completeness, but they imply no nfr-design pattern and their omission is not a rule violation.

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: none
RULES: 1,2,3,4,5,6,7,8,9,10,11
LENS-RULES: owasp:1,2,3,4,5,6,7,8
---END-PROCESS-CHECK-DATA---
