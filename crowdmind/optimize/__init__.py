"""Autoresearch-style content optimization (propose → test → keep/discard)."""

from crowdmind.optimize.autoresearch import (
    AutoresearchLoop,
    OptimizationResult,
    run_optimization,
)

__all__ = [
    "AutoresearchLoop",
    "OptimizationResult",
    "run_optimization",
]
