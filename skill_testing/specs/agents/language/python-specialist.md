# Agent Test Spec: python-specialist

## Agent Summary
Domain: Python services, libraries, APIs, data/ML pipelines, async boundaries,
type hints, package structure, dependency management, and Python-specific code review.
Does NOT own: cross-language architecture decisions, deployment ownership, or
non-Python source without coordination.
Model tier: Sonnet.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and mentions Python-specific ownership
- [ ] `tools:` includes Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is Sonnet
- [ ] Agent redirects cross-language architecture to `lead-programmer`
- [ ] Agent coordinates security/deployment with `security-engineer` or `devops-engineer`

---

## Test Cases

### Case 1: FastAPI endpoint implementation
**Input:** "Implement a FastAPI endpoint from this Product CDD."
**Expected behavior:**
- Reads the CDD and ADRs before proposing code
- Defines request/response models with type hints
- Handles validation errors with stable error codes
- Offers pytest/httpx tests

### Case 2: Out-of-domain deployment request
**Input:** "Design the full production deployment architecture."
**Expected behavior:**
- Redirects deployment ownership to `devops-engineer` or `technical-director`
- May contribute Python runtime constraints
- Does not unilaterally choose cloud architecture

---

## Protocol Compliance

- [ ] Proposes architecture before writing files
- [ ] Uses type hints and Python packaging conventions
- [ ] Keeps dependencies minimal and explicit
- [ ] Offers tests for public behavior
