# Agent Test Spec: go-specialist

## Agent Summary
Domain: Go services, CLIs, libraries, concurrency, interfaces, module layout,
error handling, observability, and Go-specific code review.
Does NOT own: product scope, deployment ownership, or non-Go source without coordination.
Model tier: Sonnet.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and mentions Go-specific ownership
- [ ] `tools:` includes Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is Sonnet
- [ ] Agent references Go interfaces, context cancellation, goroutines/channels, and errors
- [ ] Agent redirects cross-domain decisions to `lead-programmer` or `technical-director`

---

## Test Cases

### Case 1: HTTP service endpoint
**Input:** "Implement a Go API endpoint from this Product CDD."
**Expected behavior:**
- Reads CDD and ADRs before proposing code
- Defines handler/service/storage boundaries
- Uses `context.Context` for cancellation and deadlines
- Offers handler tests and integration tests where appropriate

### Case 2: Concurrency request
**Input:** "Speed this import job up with goroutines."
**Expected behavior:**
- Identifies data races, ordering constraints, and backpressure needs
- Proposes worker-pool or pipeline design before editing
- Adds tests for cancellation and error propagation

---

## Protocol Compliance

- [ ] Keeps interfaces small and package boundaries clear
- [ ] Uses explicit error handling
- [ ] Avoids goroutine leaks and uncontrolled concurrency
- [ ] Offers tests for public behavior and concurrency edge cases
