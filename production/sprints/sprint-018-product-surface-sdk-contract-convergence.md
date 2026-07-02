# Sprint 018: Product Surface And SDK Contract Convergence

> Status: Local Implementation Complete / Accepted Local
> Created: 2026-07-03
> Source: Post-Sprint-I local productization window; external gates remain operator-owned
> Plan: `C:\Users\WSMAN\.claude\plans\validated-tumbling-rabbit.md` (审查修订版)

## Goal

Converge the product surface and the TypeScript SDK / Web platform-entity
contract so the four delivery tiers (CLI / Daemon / SDK / Web) present one
consistent product menu and one platform-entity type source of truth — without
touching external gates or maturity posture. Local, executable, no external
dependencies. External gates S017-003 / W3-live / AUTH-prod / S017-007 remain
unchanged.

## Maturity Posture

Sprint 018 keeps the project at product-level Alpha / controlled PoC. It does
not authorize enterprise Beta, Production, GA, stable, or production-ready
claims.

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Background

After Sprint I (API semantic compression), the remaining local-executable gaps
are in product surface and SDK/Web contract, not structural migration. See the
plan's Context section for the full evidence. In short: platform entities are
duplicated between `web/src/types/platform.ts` and the (untyped) TS SDK; the SDK
contract gate does not read a platform-types file; there are no product-package
READMEs; the Web primary nav is `Market / Research / Portfolio / Workspace`
(inconsistent with the four-product-module口径); and the `active.md` header does
not match its tracked state.

## Decision Gates

- **D0 — `active.md` retention**: Recommended — fix the header to state the real
  tracked status; do NOT `git rm --cached` this sprint. Alternate (gitignore +
  `git rm --cached`) only if separately approved.
- **D1 — Web primary nav**: Recommended — `Market / Research / Portfolio / Quant`;
  Workspace stays reachable as the Research/Case platform container;
  Admin/Governance/Eval stay as auxiliary entries.
- **D2 — Governance/Eval UI**: Recommended — do NOT add a `GovernanceDomainView`
  or a fifth product module; keep using `/admin`, case/run detail Eval blocks,
  and `docs/start-here/eval-demo-owner.md`.

## Stories

| ID | Slice | Story (作为…我想…产出…归属…不得触碰…) | Owner |
|----|-------|----------------------------------------|-------|
| S018-001 | 0 | 作为 release-manager，登记 Sprint 018 计划 + 修 README quickstart + active.md 元数据；产出 sprint plan + 一致的三路径 quickstart；归属 governance；不得触碰 maturity posture 或外部门禁。 | lead-programmer |
| S018-002 | 1 | 作为 typescript-specialist，在 TS SDK 建立 platform entity/payload 唯一类型源（`platform-types.ts` + 导出 + 具名返回）；产出 SDK typed surface；归属 `packages/doge-sdk-typescript`；不得在 Web 维护第二套平台实体类型。 | typescript-specialist |
| S018-003 | 1 | 作为 typescript-specialist，Web 从 `doge-sdk` 导入平台类型并删除 `web/src/types/platform.ts`；产出无重复类型的 Web 客户端；归属 `web/src`；不得重新引入 Web-local platform interface。 | typescript-specialist |
| S018-004 | 2 | 作为 qa-lead，扩展 SDK contract gate 读取 `platform-types.ts` 并做 OpenAPI↔TS 属性名 parity 检查；产出回归测试 + 通过的 gate；归属 `tools/ci` + `tests`；不得降低现有 surface-token 检查。 | qa-lead |
| S018-005 | 3 | 作为 lead-programmer，为四个产品源包补 README；产出 4 × README；归属 `src/doge/products/*`；不得另造产品模块分类或违背 module-boundaries.md。 | lead-programmer |
| S018-006 | 3 | 作为 ux-designer，增强 `docs/start-here/local-analyst.md`；产出唯一 Local Analyst start-here 入口；归属 `docs/start-here`；不得新建重复 Local Analyst 文档。 | ux-designer |
| S018-007 | 4 | 作为 ui-programmer，把 Web 主导航对齐四产品模块（D1）并保留平台/治理辅助入口（D2）；产出更新后的 registry/App.vue/nav spec；归属 `web/src`；不得把 Governance/Eval 写成第五产品模块。 | ui-programmer |

## Acceptance Criteria (per slice)

**Slice 0 — Plan & state hygiene.** Sprint 018 file exists with
Goals/Scope/Non-goals/Stories/Acceptance/Verification/Maturity cap/External
gates; README Quick Start lists three explicit paths; `active.md` header matches
its tracked state (D0 recommended); `validate_docs_links.py` passes; `git ls-files
production/session-state/active.md` matches header; `git diff --check HEAD --`
clean.

**Slice 1 — TS SDK/Web contract.** New `platform-types.ts` hosts all platform
interfaces; `index.ts` exports them; `platform.ts` returns named entity types;
`web/src/types/platform.ts` deleted; 10 consumers import from `doge-sdk`;
unnecessary `as unknown as` casts removed; SDK `npm test && npm run build` and
web `npm test && npm run build` pass; no active `web/src/types/platform`
references.

**Slice 2 — Contract gate.** `sdk-contract-check.py` reads `platform-types.ts`
and checks OpenAPI↔TS property-name parity for the key schemas; regression tests
cover missing-property-fails and current-shapes-passes; `sdk-contract-check.py`
and `validate_import_boundaries.py` pass.

**Slice 3 — Product docs.** Four `src/doge/products/*/README.md` exist (derived
from module-boundaries/modules/source-layout authorities);
`docs/start-here/local-analyst.md` enhanced, no duplicate; `validate_docs_links.py`
and `validate_alpha_maturity_honesty.py` pass; no new false maturity claims.

**Slice 4 — Web nav.** `PRIMARY_SCENARIO_NAV_ITEMS` = `Market / Research /
Portfolio / Quant` (D1); `App.vue` active-state and `productNavigation.spec.ts`
synced; Workspace deep links still reachable; no `GovernanceDomainView` product
module (D2); web `npm test && npm run build` pass.

## Verification Plan

```bash
python scripts/validate_docs_links.py
python scripts/validate_alpha_maturity_honesty.py
python scripts/validate_governance_yaml_shape.py
git diff --check HEAD --
python tools/ci/sdk-contract-check.py
cd packages/doge-sdk-typescript && npm test && npm run build
cd web && npm test && npm run build
python scripts/validate_import_boundaries.py
python -m pytest tests/unit/layer_gates tests/unit/architecture tests/unit/governance -q
python scripts/validate_plan_closure_gate.py --allow-open
python scripts/validate_plan_closure_gate.py   # expected to fail until S017-003/W3-live/AUTH-prod/S017-007 close
```

## Non-Goals

- No physical migration of evidence/use-case services into `platform/products`;
  no `core/` re-layout.
- No Python SDK response typing (Python stays on backend Pydantic + OpenAPI + SDK
  dict returns).
- No new live/provider/IdP/registry evidence; S017-003, W3-live, AUTH-prod,
  S017-007 are not closed.
- No restoration of `src/macro`, `src/micro`, the retired PyQt dashboard,
  `doge.application.composition`, or retired shims.
- Governance/Eval is not expressed as a fifth product module.
- No commit unless the user explicitly requests it.

## External Gates Preserved

| Gate | Status |
|------|--------|
| S017-002 (Kimi Coding v1) | passed |
| S017-006 (screen-reader manual) | passed |
| S017-003 (financial provider fixture) | open — operator |
| W3-live (analyst benchmark) | open — operator |
| AUTH-prod (enterprise auth production) | open — operator |
| S017-007 (SDK registry release) | open — operator |
