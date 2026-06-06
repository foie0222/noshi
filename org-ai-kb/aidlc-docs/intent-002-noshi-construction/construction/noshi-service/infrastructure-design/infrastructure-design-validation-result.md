# Infrastructure Design — Validation Result (noshi-service)

**Status:** PASS
**Attempt:** 2 (re-validation)
**Validated artifacts:** `infrastructure-design.md`, `deployment-architecture.md`
**Answered questions:** `infrastructure-design-questions.md`

Re-validation focus: confirm Rule 11 (per-service cost estimates tied to expected load) — which failed in attempt 1 — is resolved, confirm Rule 12 (IaC tool + module/stack boundaries), and confirm no regressions across all other rules and OWASP lens rules.

## Scripts invoked

- Skill scripts directory `.kiro/skills/aidlc-infrastructure-design/scripts/` is **absent**. No scripts to run.
- Lens `.kiro/skills/aidlc-owasp/scripts/` is **absent**. No scripts to run.

## Rules checked (infrastructure-design validation-spec)

| Rule | Description | Result |
|------|-------------|--------|
| 1 | Both artifacts present and non-empty | PASS |
| 2 | Every logical component mapped to a concrete service | PASS |
| 3 | Services consistent with tech-stack-decisions | PASS |
| 4 | NFRs with infra implications addressed by concrete mechanism | PASS |
| 5 | Scaling strategy references scalability requirements (triggers/thresholds) | PASS |
| 6 | Failover/recovery maps to RTO/RPO | PASS |
| 7 | Security infra consistent with NFR security + cross-cutting | PASS |
| 8 | Inter-unit connectivity consistent with units-of-work-dependency | PASS (n/a) |
| 9 | Platform assumptions explicitly stated | PASS |
| 10 | Concrete and deployable (no abstract placeholders) | PASS |
| 11 | Cost estimates present per service, referencing expected load | **PASS (resolved)** |
| 12 | IaC tool recommended + module/stack boundaries described, consistent with TSD | **PASS (resolved)** |

### Notes per rule
- **Rule 1:** Both artifacts present and substantive. No regression.
- **Rule 2:** LC-1 (SQS+DLQ), LC-2 (S3), LC-3 (in-app adapter ResiliencePolicy), LC-4 (Cognito/OIDC), LC-5 (DynamoDB AuditEntry + CloudWatch Logs), LC-6 (CloudWatch + X-Ray), LC-7 (KMS) all mapped. App layer (BFF/API → API Gateway + Lambda, 抽出ワーカー → Lambda), data store → DynamoDB, front delivery → S3+CloudFront, secrets → Secrets Manager. No component left unmapped.
- **Rule 3:** DynamoDB (TSD-3), SQS+DLQ (TSD-4), S3 signed-URL (TSD-5), OIDC/Cognito (TSD-7), Lambda+API Gateway (TSD-1), React+S3+CloudFront (TSD-2), Docker local (TSD-8), AWS CDK IaC. No engine substitution; all consistent with the AWS + Docker-local stack. The newly added cost table and IaC stacks introduce no inconsistent service choices.
- **Rule 4:** NFR-P1/P2/P3, S1/S2/S3, A1/A2/A3, SE1–SE7, R1–R3, O1–O3, D1–D3 each have a concrete mechanism (autoscale Lambda, SQS buffering, on-demand DynamoDB, PITR, KMS, WAF rate limit, structured logs/X-Ray, DLQ alarms, ap-northeast-1 residency).
- **Rule 5:** Scaling references NFR-S1 (serverless autoscale absorbing seasonal burst), NFR-S2 (SQS buffer + worker horizontal scale), NFR-S3 (DynamoDB on-demand for spikes). Concrete triggers present: visibility timeout 60s, maxReceiveCount 3 → DLQ; DLQ-depth CloudWatch alarm. (Worker autoscale threshold 滞留>100 defined upstream in P-ASY-3.)
- **Rule 6:** RTO ≤ 4h / RPO ≤ 24h stated explicitly, mapped to DynamoDB PITR + S3 versioning; single-region MVP limitation documented (NFR-A1 99%). No hidden gap.
- **Rule 7:** KMS at-rest (SE2), TLS in-transit, least-privilege IAM per Lambda, Secrets Manager, owner-scope via DynamoDB PK + BFF (A01/cross-cutting), private S3 + short-lived signed URLs, append-only audit (A09). Consistent with cross-cutting auth model and data classification.
- **Rule 8:** noshi-service is the single MVP unit; no units-of-work / units-of-work-dependency artifacts exist and no inter-unit dependencies are declared, so no inter-unit connection is missing. Not applicable.
- **Rule 9:** AWS, region ap-northeast-1, AWS CDK IaC, dev/prod + local Docker explicitly stated. No implicit undocumented infra dependency.
- **Rule 10:** Specific services with configurations throughout (HTTP API, SQS standard + DLQ params, S3 SSE-KMS/versioning/signed-URL TTL, DynamoDB GSI/PITR/TTL/on-demand, Cognito token TTLs, KMS rotation). No abstract placeholders.
- **Rule 11 (RESOLVED):** `infrastructure-design.md` now contains a "コスト概算" section: a per-service monthly USD table covering Lambda (BFF+worker), API Gateway (HTTP API), DynamoDB (on-demand), S3, SQS, CloudFront, Cognito, KMS, Secrets Manager, and CloudWatch/X-Ray, totaling ~$10–40/mo for MVP. The section header and individual rows reference the expected load from `nfr-requirements.md` — NFR-D1 (数千ユーザー / 〜数百レコード/ユーザー, incl. PITR) and NFR-S1 (seasonal burst, absorbed by usage-based pricing). A caveat states the figures are order-of-magnitude, usage-driven, and to be re-evaluated after load measurement. Rule 11 (estimates per service, may be approximate, must reference expected load) is satisfied.
- **Rule 12 (RESOLVED):** `deployment-architecture.md` recommends AWS CDK (consistent with infra-design and Q1 answer) and now defines resource-grouping stack/module boundaries: NetworkStack (WAF/cert/CloudFront base), DataStack (DynamoDB+GSI, S3, KMS — stateful, deletion protection), MessagingStack (SQS/DLQ), AuthStack (Cognito/external IdP), ApiStack (API Gateway, BFF Lambda, IAM, Secrets refs), WorkerStack (worker Lambda + SQS event source), FrontendStack (S3 hosting + CloudFront). Explicit stateful (Data/Auth) vs stateless (Api/Worker/Frontend) separation and dev/prod separation via separate stack instances/accounts. Consistent with tech-stack-decisions.

## Lens rules checked — owasp (stage = infrastructure-design → All Stages only)

Stage-specific OWASP sections (`requirements-analysis/user-stories` and `application-design/functional-design/nfr-design/code-generation`) do NOT include `infrastructure-design`, so only the All Stages section (4 rules) applies.

| Rule | Description | Result |
|------|-------------|--------|
| 1 | No auth mechanism contradicting cross-cutting auth model | PASS |
| 2 | No plaintext credentials/secrets/restricted data | PASS |
| 3 | Session/token/credential storage follows least privilege + expiration/rotation | PASS |
| 4 | Security-relevant actions have logging/audit coverage | PASS |

### Notes per lens rule
- **owasp Rule 1:** Cognito OIDC + BFF token verification + owner-scope (A01) enforced via DynamoDB PK-embedded userId. Consistent with cross-cutting `owner` role and `resource.ownerId == session.userId` policy. No contradiction.
- **owasp Rule 2:** Secrets in AWS Secrets Manager (least-privilege Lambda retrieval); KMS at-rest (DynamoDB/S3); SSE-KMS on S3; TLS in transit. AuditSink records "restricted は識別子/マスクのみ" — no plaintext restricted data. The new cost/IaC content introduces no plaintext-secret flow.
- **owasp Rule 3:** Least-privilege IAM per Lambda. Token expiry (access 15m / refresh 14d), revocation, auth rate limiting (WAF/Cognito). KMS key rotation enabled. Signed URLs short-lived (TTL 5m). Compliant.
- **owasp Rule 4:** Security events → DynamoDB AuditEntry (append-only, A09) + CloudWatch Logs; authz-failure metrics/alarms in CloudWatch; X-Ray tracing. Audit coverage present.

## Clarification consistency

Artifacts are consistent with all answers in `infrastructure-design-questions.md` (Q1 service mapping, Q2 region/residency ap-northeast-1, Q3 dev/prod + local Docker, Q4 network/security boundaries). No drift.

## Completeness

The attempt-1 failure (Rule 11) is fully addressed, and the previously noted Rule 12 weakness is now resolved. The added cost table and IaC stack boundaries did not introduce inconsistencies with upstream tech-stack-decisions, NFR requirements, or cross-cutting standards. No regressions detected across Rules 1–12 or the OWASP All-Stages rules.

## Findings

None.

## Recommendations

None required for pass. (Optional, non-blocking: when the real OcrLlmPort provider is selected and production load is measured, refresh the cost table per its own caveat.)

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: none
RULES: 1,2,3,4,5,6,7,8,9,10,11,12
LENS-RULES: owasp:1,2,3,4
---END-PROCESS-CHECK-DATA---
