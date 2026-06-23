# Platformization Consolidation Phase F: Web Navigation

Date: 2026-06-23

## Scope

Phase F consolidated the Web shell around product-domain navigation while
preserving existing deep links.

This phase changed only the Web information architecture layer. It did not
remove legacy views, change backend routes, change SDK contracts, or modify the
existing Vite/TypeScript configuration files.

## Implemented

- Added product-domain shell routes:
  - `/home`
  - `/research`
  - `/market`
  - `/portfolio`
  - `/quant`
  - `/admin`
- Changed the platform-shell root redirect from `/workspaces` to `/home`.
- Replaced the top toolbar's platform-specific nav items with:
  - Home
  - Research
  - Market
  - Portfolio
  - Quant
  - Admin
- Preserved legacy direct routes:
  - `/research-agent`
  - `/scanner`
  - `/cn-archive`
  - `/us-archive`
  - `/insights`
  - `/analysis`
- Registered the new domain views in the split-pane view registry.
- Added a reusable `DomainLandingView` for domain entry surfaces.
- Added a Portfolio domain side panel that reuses the existing portfolio CSV
  importer and stores the imported portfolio id in the existing agent store.
- Added Web regression coverage for product-domain routes, legacy deep links,
  and split-pane view registry entries.

## Compatibility Notes

`/research-agent` remains a working compatibility entry. It is now positioned as
the Research Case execution area rather than as a top-level product module.

The old market and report views remain directly addressable. The dominant shell
now points users through `/market`, `/research`, `/portfolio`, and `/quant`
instead of exposing every historical view as a peer top-level destination.

## Verification

Commands were run from `web/` with the local Node path prepended:

```text
npm test
npm run build
```

Results:

```text
Vitest: 14 files passed, 84 tests passed.
Build: vue-tsc and Vite production build passed.
```

## Phase F Close Criteria

- Web exposes one dominant product-domain shell: satisfied.
- Legacy direct routes remain available: satisfied.
- Research Agent remains compatible: satisfied.
- Split-pane registry recognizes the new domain views: satisfied.
- Feature-flag behavior remains intact for platform-shell routes: satisfied.
