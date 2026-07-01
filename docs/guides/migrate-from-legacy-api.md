# Migrate From Legacy API

Use this guide when an old caller still targets `/api/*` and needs a path to the
daemon contract. Full route details remain in [../API.md](../API.md).

## Your 3-step first path

1. Identify the legacy behavior.

   Record the current `/api/*` method, path, caller, and response fields. Do not
   add new platform-only behavior to the legacy route while migrating.

2. Find the `/v1` or SDK destination.

   Use [../API.md](../API.md) for the canonical route table. For client code,
   prefer [use-python-sdk.md](use-python-sdk.md) or
   [use-typescript-sdk.md](use-typescript-sdk.md) instead of raw HTTP when a
   maintained SDK method exists.

3. Preserve compatibility until removal gates are met.

   Keep deprecation headers and migration hints on the old path. Removal requires
   parity tests, migration notes, and the sunset criteria documented by the
   compatibility registry.

## Checks Before You Stop

- The new caller uses `/v1` or an SDK client.
- The old route did not gain new product-only behavior.
- Contract tests cover the migrated path.
- Compatibility notes name the replacement surface.

## Related References

- API reference: [../API.md](../API.md)
- Compatibility surfaces: [../architecture/compatibility-surfaces.md](../architecture/compatibility-surfaces.md)
- File structure policy: [../architecture/file-structure-policy.md](../architecture/file-structure-policy.md)
- Operations runbook: [../operations/runbook.md](../operations/runbook.md)

## When To Leave This Page

Leave for [run-daemon-gateway.md](run-daemon-gateway.md) when you need to test
the replacement route manually. Leave for [architecture-reviewer.md](../start-here/architecture-reviewer.md)
when a shim or removal decision needs review.
