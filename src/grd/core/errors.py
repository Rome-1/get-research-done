"""Exception hierarchy for GRD.

All GRD exceptions inherit from GRDError, enabling callers to catch the entire
package's errors with a single ``except GRDError``.

Hierarchy (errors defined in this file)::

    GRDError
    ├── ValidationError(ValueError)     # cross-cutting input validation
    ├── StateError(ValueError)          # state.py
    ├── ConventionError(ValueError)     # conventions.py
    ├── ResultError(ValueError)         # results.py
    │   ├── ResultNotFoundError(KeyError)
    │   └── DuplicateResultError(ValueError)
    ├── QueryError(ValueError)          # query.py
    ├── ExtrasError(ValueError)         # extras.py
    │   └── DuplicateApproximationError(ValueError)
    ├── PatternError                    # patterns.py
    ├── TraceError                      # trace.py
    └── ConfigError(ValueError)         # config.py

Errors defined in their owning modules (inherit GRDError):

    ├── PhaseError                           # phases.py
    │   ├── PhaseNotFoundError
    │   ├── PhaseValidationError
    │   ├── PhaseIncompleteError
    │   ├── RoadmapNotFoundError
    │   └── MilestoneIncompleteError
    ├── FrontmatterParseError(ValueError)    # frontmatter.py
    └── FrontmatterValidationError(ValueError) # frontmatter.py

Domain error classes also inherit from their stdlib counterpart (KeyError,
ValueError) where applicable so existing generic exception handling still
behaves as expected.
"""

from __future__ import annotations

__all__ = [
    "ConfigError",
    "ConventionError",
    "DuplicateApproximationError",
    "DuplicateResultError",
    "ExtrasError",
    "GRDError",
    "PatternError",
    "QueryError",
    "ResultError",
    "ResultNotFoundError",
    "StateError",
    "TraceError",
    "ValidationError",
]

# ─── Base ────────────────────────────────────────────────────────────────────


class GRDError(Exception):
    """Base exception for all GRD errors."""


# ─── Domain Errors ───────────────────────────────────────────────────────────


class StateError(GRDError, ValueError):
    """Error in GRD state management."""


class ConventionError(GRDError, ValueError):
    """Error in convention lock operations."""


class ResultError(GRDError, ValueError):
    """Error in intermediate result tracking."""


class ResultNotFoundError(ResultError, KeyError):
    """Requested result ID does not exist in state."""

    def __init__(self, result_id: str) -> None:
        self.result_id = result_id
        super().__init__(f'Result "{result_id}" not found')

    def __str__(self) -> str:
        return Exception.__str__(self)


class DuplicateResultError(ResultError, ValueError):
    """A result with the given ID already exists."""

    def __init__(self, result_id: str) -> None:
        self.result_id = result_id
        super().__init__(f'Result with id "{result_id}" already exists')


class QueryError(GRDError, ValueError):
    """Error in cross-phase query operations."""


class ExtrasError(GRDError, ValueError):
    """Error in approximation/uncertainty/question/calculation tracking."""


class DuplicateApproximationError(ExtrasError, ValueError):
    """An approximation with the given name already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f'Approximation "{name}" already exists')


class PatternError(GRDError):
    """Error in pattern library operations."""


class TraceError(GRDError):
    """Error in execution trace operations."""


class ConfigError(GRDError, ValueError):
    """Error loading or validating GRD configuration."""


class ValidationError(GRDError, ValueError):
    """General validation error for GRD operations.

    Use domain-specific errors when possible. This is for cross-cutting
    validation that doesn't belong to a specific module.
    """
