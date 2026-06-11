# Agent Test Spec: rust-specialist

## Agent Summary
Domain: Rust libraries, CLIs, services, async runtimes, ownership/lifetime
modeling, error types, performance-sensitive modules, and Rust-specific code review.
Does NOT own: cross-language architecture, product scope, or deployment ownership.
Model tier: Sonnet.

---

## Static Assertions (Structural)

- [ ] `description:` field is present and mentions Rust-specific ownership
- [ ] `tools:` includes Read, Glob, Grep, Write, Edit, Bash
- [ ] Model tier is Sonnet
- [ ] Agent references ownership, lifetimes, traits, error handling, and async runtime choices
- [ ] Agent redirects deployment/security decisions when outside Rust code

---

## Test Cases

### Case 1: CLI command implementation
**Input:** "Implement this CLI command from the Product CDD."
**Expected behavior:**
- Reads CDD, ADRs, and CLI UX notes
- Defines typed arguments and structured errors
- Separates stdout/stderr and returns meaningful exit codes
- Offers unit and command-level tests

### Case 2: Performance-sensitive library
**Input:** "Optimize this parser without changing behavior."
**Expected behavior:**
- Establishes current behavior and benchmarks first
- Uses idiomatic ownership/borrowing rather than unsafe shortcuts
- Flags any unsafe block for explicit approval and review

---

## Protocol Compliance

- [ ] Proposes trait/module boundaries before broad edits
- [ ] Keeps error types explicit and documented
- [ ] Uses tests and benchmarks for behavior/performance claims
- [ ] Avoids unsafe code unless justified and approved
