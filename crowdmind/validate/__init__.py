"""
CrowdMind Validate Module

Validate product ideas with AI personas using EDSL.
"""

from crowdmind.validate.panel import run_evaluation, run_ab_test
from crowdmind.validate.personas import (
    Persona,
    PersonaPack,
    PERSONA_PACKS,
    get_personas,
    get_balanced_personas,
)

__all__ = [
    "run_evaluation",
    "run_ab_test",
    "Persona",
    "PersonaPack",
    "PERSONA_PACKS",
    "get_personas",
    "get_balanced_personas",
]
