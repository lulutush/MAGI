"""Portable MAGI: advisory routing and declarative checks, with no implicit I/O."""

__version__ = "0.1.0"

from .core import evaluate_gate, route, validate_artifact

__all__ = ["__version__", "route", "evaluate_gate", "validate_artifact"]
