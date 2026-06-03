# OWASP Security Lens — Validation Spec

These rules are checked by the validator at every stage where this lens is active. Rules are organized into sections by stage applicability. The validator checks "All Stages" rules everywhere, plus any stage-specific section that matches the current skill's stage.

## Rules

### All Stages

Rules in this section are checked at every stage where this lens is active.

1. Artifacts must not introduce authentication or authorization mechanisms that contradict the auth model established in the lens answers or upstream `cross-cutting.md`. Contradictions must be flagged.
2. No artifact may store, log, or transmit credentials, secrets, or restricted data in plaintext. If an artifact describes such a flow, it must specify encryption or redaction.
3. If the artifacts introduce session management, token handling, or credential storage, they must follow the principle of least privilege and define expiration/rotation policies.
4. Security-relevant actions (authentication attempts, authorization failures, data access, configuration changes) must have logging or audit trail coverage in the design. Missing audit coverage for security events is a failure.

### requirements-analysis, user-stories

Rules in this section are checked only when the current stage is `requirements-analysis` or `user-stories`.

1. Every capability with security implications must be traceable to at least one security-related requirement or story (functional or non-functional).
2. Sensitive data types must be identified with at minimum a high-level classification (e.g., "user credentials are restricted", "rental history is internal"). Full field-level classification is not required at this stage.

### application-design, functional-design, nfr-design, code-generation

Rules in this section are checked only when the current stage is `application-design`, `functional-design`, `nfr-design`, or `code-generation`.

1. Every data flow or data field introduced in the artifacts must have an explicit classification (public, internal, confidential, or restricted). Unclassified data is a failure.
2. Every trust boundary crossing identified or implied in the artifacts must have a documented validation/encoding strategy. Unprotected boundary crossings are a failure.
3. Every external input surface (API endpoint, form field, file upload, URL parameter, message payload) must have input validation documented or implied by the design. Unvalidated external inputs are a failure.
4. Error handling described in artifacts must not leak sensitive information (stack traces, internal paths, database schemas, credentials). Error responses to external actors must be generic.
