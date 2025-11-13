"""Deprecated module: use ``src.core.retry`` instead.

This module used to contain retry utilities based on tenacity. The project has
standardized on a dependency-light implementation in ``src.core.retry``.
The file is kept only for backward compatibility and intentionally provides no
runtime API. Import from ``src.core.retry`` in new code.
"""

__all__: list[str] = []
