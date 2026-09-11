"""Public package name for the ACSL-C implementation.

The ``acsl_c`` namespace remains available for compatibility with research
configs and existing installations.
"""

import acsl_c as _implementation

__all__ = list(_implementation.__all__)
globals().update({name: getattr(_implementation, name) for name in __all__})
