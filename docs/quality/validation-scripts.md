# Validation Scripts

This page maps documentation validators for reviewers.

## Docs Validators

- `scripts/validate_docs_links.py`
- `scripts/validate_no_stale_counts.py`
- `scripts/validate_docs_authority.py`
- `scripts/validate_docs_guides_structure.py`
- `scripts/validate_docs_length.py`
- `scripts/validate_docs_maturity_claims.py`
- `scripts/generate_docs_status.py --check`

## Maturity Validators

- `scripts/validate_alpha_maturity_honesty.py`
- `scripts/validate_governance_yaml_shape.py`

## Test Gate

The main governance test is
`tests/unit/governance/test_docs_consistency.py`.
