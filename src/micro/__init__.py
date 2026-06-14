"""Legacy market-data micro modules (brownfield, under clean-architecture migration).

These modules (``database``, ``market_scanner``, ``momentum_scanner``,
``tdx_downloader``, ``industry_analyzer``, ``tdx_loader``) are the pre-migration
implementation surface. They remain importable as the ``micro`` package so the
clean-architecture target under :mod:`doge` can delegate to them without
``sys.path`` shims (ADR-0001 forbidden pattern ``sys_path_insert``). Full
retirement is sequenced under the clean-architecture migration (Module #12).
"""
