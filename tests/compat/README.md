# Compatibility Tests

This directory is reserved for backwards-compatibility checks for deprecated
shim surfaces such as `src.api`.

New canonical API tests should import `doge.interfaces.api` directly. Tests in
this directory may intentionally import deprecated shims to verify that old
operator entrypoints still fail closed or redirect correctly during the
deprecation window.
