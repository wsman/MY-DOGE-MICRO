# Sprint 047 - Third-party Slot Install Preview

Status: Local implementation complete / local verification passed
Date: 2026-07-07

## Summary

Sprint 047 implements the controlled third-party local slot install preview
from `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds manifest-only install, sidecar signature metadata validation,
enterprise allowlist policy, install settings, and `doge slots install`.

This sprint does not complete a third-party plugin execution ecosystem.

## Scope

- Add ADR-0057 and this sprint CDD/governance trail.
- Add `SlotInstaller`, `SlotInstallPolicy`, `SlotInstallResult`,
  `SlotSignatureVerification`, and `verify_slot_signature()`.
- Add `DOGE_FEATURE_SLOT_INSTALL` lifecycle metadata and settings field.
- Add `DOGE_SLOT_INSTALL_DIR`, `DOGE_SLOT_ENTERPRISE_ALLOWLIST`,
  `DOGE_SLOT_TRUSTED_SIGNERS`, and `DOGE_SLOT_ALLOW_UNSIGNED_LOCAL`.
- Expose `feature.slot_install` through capability discovery.
- Add bootstrap `install_slot()` helper.
- Include installed manifest directory in manifest-only discovery when install
  flag is enabled.
- Add CLI `doge slots install`.
- Add focused install, settings, capability, CLI, and kernel discovery tests.
- Update configuration docs and the OpenClaw-like plan file.

## Explicitly Out of Scope

- Provider entrypoint import or arbitrary Python plugin execution.
- Marketplace, registry download, or remote install.
- Cryptographic signature format.
- HTTP install API or SDK slot client methods.
- YAML manifest parsing.
- OS sandboxing, subprocess isolation, network interception, filesystem
  mediation, or database/secret access interception.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification passed:

- Focused install/settings/capability/CLI/kernel suite passed: 65 tests.
- Broad slot parity suite passed: 173 tests, with 2 known FastAPI deprecation
  warnings.
- SDK contract passed: 15 surfaces and 15 entity parity checks.
- Import boundaries, docs authority, docs links, docs maturity claims,
  ADR/CDD maturity honesty, ADR index, governance YAML, acceptable-open plan
  closure, and WSL/Windows whitespace checks passed.
- External/operator closure posture remains intentionally open: 2 passed,
  4 open, 0 failed, 0 invalid.
