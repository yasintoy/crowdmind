"""
CrowdMind - AI-Powered Research & Validation for Products

Validate your product ideas with simulated user panels,
research market pain points, and generate feature ideas.
"""

__version__ = "0.2.3"

from crowdmind.validate.panel import run_evaluation as analyze
from crowdmind.validate.panel import run_evaluation as validate
from crowdmind.research.multi import run_multi_research as research
from crowdmind.validate.personas import Persona, PersonaPack

__all__ = [
    "analyze",
    "validate", 
    "research",
    "Persona",
    "PersonaPack",
    "__version__",
]
