---
name: aidlc-owasp
description: |
  AI-DLC OWASP security lens. Applies OWASP security principles as a perspective across the entire development lifecycle. When active, every stage's builder considers security implications and every stage's validator checks for security gaps.

  This is a lens — it does not run as a discrete step. It is activated during workflow-composition and its definitions are injected into every builder and validator invocation.
metadata:
  type: lens
  phase: lens
  stage: owasp
  applies-to: "all"
  default-activation: "true"
---

# OWASP Security Lens

Embed security thinking at every stage of the development lifecycle, grounded in the OWASP Top 10 and secure-by-design principles. This lens ensures that security is not an afterthought bolted on at the end, but a consideration woven into requirements, design, implementation, and validation from the start.

## Purpose

Shift security left. Every artifact produced during the lifecycle should reflect awareness of:
- What can go wrong (threats)
- What is being protected (assets and data classification)
- How protection is achieved (controls)
- What happens when protection fails (failure modes)

## Definitions

### Data Classification Levels

- **Public** — no confidentiality requirement; disclosure causes no harm
- **Internal** — default classification; not intended for public consumption but low impact if disclosed
- **Confidential** — disclosure causes material harm; requires access control and encryption
- **Restricted** — highest sensitivity (PII, credentials, financial data, health records); requires strict access control, encryption at rest and in transit, audit logging

### Trust Boundaries

A trust boundary exists wherever data crosses between zones of different trust levels:
- External user → application edge (always untrusted)
- Application → database (trusted but verified)
- Service → service (trust depends on network model)
- Application → external system (untrusted)

Every trust boundary requires: input validation on entry, output encoding on exit, authentication of the caller, and authorization of the action.

### OWASP Top 10 Categories (2021)

1. **A01: Broken Access Control** — restrictions on authenticated users not properly enforced
2. **A02: Cryptographic Failures** — failures related to cryptography leading to data exposure
3. **A03: Injection** — untrusted data sent to an interpreter as part of a command or query
4. **A04: Insecure Design** — missing or ineffective security controls in the design itself
5. **A05: Security Misconfiguration** — insecure default configurations, incomplete setups
6. **A06: Vulnerable and Outdated Components** — using components with known vulnerabilities
7. **A07: Identification and Authentication Failures** — weaknesses in identity verification
8. **A08: Software and Data Integrity Failures** — code and infrastructure without integrity verification
9. **A09: Security Logging and Monitoring Failures** — insufficient logging, detection, and response
10. **A10: Server-Side Request Forgery (SSRF)** — fetching remote resources without validating user-supplied URLs

### Secure Design Principles

- **Defence in depth** — multiple layers of security controls; no single point of failure
- **Least privilege** — grant minimum access required for the task
- **Fail secure** — on failure, deny access rather than grant it
- **Separation of duties** — no single actor can complete a sensitive operation alone
- **Input validation** — validate all input at trust boundaries; reject by default
- **Output encoding** — encode output appropriate to the context (HTML, SQL, URL, etc.)
- **Secure defaults** — systems are secure out of the box; insecurity requires explicit opt-in

## Principles for the Builder

When producing artifacts at any stage, consider:

1. **Identify assets** — what data or capabilities in this artifact are worth protecting? Classify data per the levels above.
2. **Identify threats** — what could go wrong? Which OWASP Top 10 categories are relevant to what you're designing or building?
3. **Define controls** — for each identified threat, what control mitigates it? Controls should be specific and traceable.
4. **Document trust boundaries** — where does data cross trust levels? What validation/encoding happens at each crossing?
5. **Consider failure modes** — what happens when a security control fails? Does the system fail open (dangerous) or fail closed (safe)?
6. **Preserve auditability** — can security-relevant actions be traced? Is there enough logging to detect and investigate incidents?

These principles apply differently at each stage — the builder interprets them in context:
- At requirements: capture security requirements, identify sensitive data, define compliance needs
- At stories: include abuse cases and attacker personas alongside happy-path stories
- At design: identify trust boundaries, define auth enforcement points, classify data flows
- At functional design: encode authorization rules, input validation, session management as business rules
- At NFR assessment: quantify security targets (encryption standards, auth token lifetimes, rate limits)
- At code generation: parameterized queries, output encoding, CSRF protection, secure headers, secrets management

## Question Guidance

When this lens is activated, ask the following during workflow-composition to tailor security considerations to the intent:

- What is the sensitivity of the data this system handles? (public, internal, confidential, restricted — or a mix?)
- Are there compliance requirements? (GDPR, HIPAA, PCI-DSS, SOC2, FedRAMP, etc.)
- What is the authentication model? (OAuth2, SAML, API keys, mTLS, session-based, etc.)
- Is this system internet-facing, internal-only, or a mix?
- Are there known threat actors or attack vectors specific to this domain?
- What is the acceptable risk tolerance? (zero-tolerance for data breach vs. balanced risk acceptance for internal tools)
