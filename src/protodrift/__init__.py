"""Detect drift between .proto sources and committed generated stubs.

Read-only, deterministic, stdlib-only. Detection is based on the working tree:
each generated stub is mapped back to its source .proto (embedded header first,
filename convention second) and the two mtimes are compared.
"""

from protodrift.scan import SEVERITIES, Finding, scan

__all__ = ["SEVERITIES", "Finding", "scan"]
__version__ = "0.1.0"