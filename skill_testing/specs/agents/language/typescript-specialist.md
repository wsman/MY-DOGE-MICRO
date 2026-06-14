# Agent Test Spec: typescript-specialist

## Agent Summary
Domain: TypeScript applications, Node services, frontend code, type modeling,
API clients, package scripts, and TypeScript-specific code review.
Does NOT own: product design, visual direction, deployment ownership, or
non-TypeScript source without coordination.
Model tier: Sonnet.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and mentions TypeScript-specific ownership
- [ ] `tools:` includes Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is Sonnet
- [ ] Agent respects UX specs and ADRs before implementation
- [ ] Agent redirects security/deployment ownership to the appropriate agents

---

## Test Cases

### Case 1: Product web workflow
**Input:** "Implement the billing settings workflow from the UX spec."
**Expected behavior:**
- Reads Product CDD, UX spec, and ADRs
- Defines typed state and API client boundaries
- Handles loading, empty, error, and success states
- Offers component/e2e tests

### Case 2: API client generation
**Input:** "Build a typed client for this OpenAPI schema."
**Expected behavior:**
- Checks schema version and generated-client constraints
- Produces typed request/response surfaces
- Documents error handling and retry boundaries
- Does not change API semantics without design approval

---

## Protocol Compliance

- [ ] Uses strict typing and avoids `any` unless justified
- [ ] Preserves UI accessibility requirements from UX docs
- [ ] Keeps package/dependency changes explicit
- [ ] Offers tests for public behavior
