# Release Notes

## Customer Delivery Ready Release

This release establishes the template as a stable customer delivery baseline
for new game projects, new product projects, and existing project adoption.

### What Is Included

- Clear Start Here paths for new Game projects, new Product projects, and
  existing project adoption.
- A seven-phase workflow catalog used as the required-step source of truth.
- Governed advisory gates with `PASS`, `CONCERNS`, and `FAIL` outcomes.
- Game and Product branches inside the same command surface.
- Technical Setup baseline covering stack setup, architecture, ADRs,
  architecture review, control manifest, accessibility requirements, and tests.
- Canonical story paths under `production/epics/[epic-slug]/`.
- Canonical QA evidence under `production/qa/evidence/`.
- Full strict lint coverage for all skill files.

### Important Upgrade Notes

- Use `/constitute` as the unified entry command.
- Treat `workflow-catalog.yaml` as the required-step source of truth.
- Keep `/art-bible` as Concept optional for Game projects; it is not a Technical
  Setup blocker.
- Release now follows `/release-checklist` -> `/launch-checklist` ->
  `/team-release`.

### Validation Model

- Template Consistency CI is configured for Ubuntu, macOS, and Windows runners.
- Windows local hook execution requires Git Bash; Windows toast notifications
  are optional and fall back to plain hook output when unavailable.
- Validation status: recorded on the GitHub Release or annotated tag for the
  immutable release commit, not self-referenced from this committed Markdown file.
- Required workflow: `Template Consistency`.
- Required release evidence: release commit SHA, GitHub Actions run ID, and PASS
  result for `ubuntu-latest`, `macos-latest`, and `windows-latest`.
- Customer acceptance checklist: `docs/CUSTOMER-ACCEPTANCE.md`.
- The earlier `v0.1.0-rc.1` prerelease remains available as the historical
  candidate evidence for this stable release line.
