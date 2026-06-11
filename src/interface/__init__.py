"""Legacy desktop/GUI interface modules (PyQt6 dashboard + analysis GUI).

Brownfield, under clean-architecture migration. Kept importable as the
``interface`` package so the PyQt entrypoints resolve without ``sys.path``
shims (ADR-0001 forbidden pattern ``sys_path_insert``).
"""
