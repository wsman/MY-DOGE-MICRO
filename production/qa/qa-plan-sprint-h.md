# Sprint H QA Plan - Compatibility Surface Governance

Date: 2026-07-01

Sprint H is local architecture/governance hardening only. It does not close
external gates and does not promote runtime maturity.

## QA Cases

| WP | Area | Evidence Command |
|----|------|------------------|
| WP0 | Current-head and maturity honesty | `py -3 scripts\validate_alpha_maturity_honesty.py` |
| WP1 | Shim behavior guardrails | `py -3 -m pytest tests\unit\architecture\test_shim_behavior_guards.py -q` |
| WP2 | Composition public-surface allowlist | `py -3 -m pytest tests\unit\architecture\test_composition_allowlist.py -q` |
| WP3 | Full architecture guard suite | `py -3 -m pytest tests\unit\architecture -q` |
| WP4 | Docs/governance validators | docs links, governance YAML shape, plan closure `--allow-open`, `git diff --check` |

## Maturity Guard

- `production_ready: false` must remain unchanged.
- `stable_declaration: forbidden` must remain unchanged.
- `level_3_sdk_platform: experimental` must remain unchanged.
- Strict closure gate must remain open until `S017-003`, `W3-live`,
  `AUTH-prod`, and `S017-007` have real completed evidence.
