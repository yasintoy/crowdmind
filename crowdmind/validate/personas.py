"""
Persona Definitions and Preset Packs

Defines user personas for product validation surveys.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import random


@dataclass
class Persona:
    """A user persona for validation surveys."""
    
    persona: str  # Short description
    background: str  # Detailed background
    skepticism: str = "medium"  # low, medium, high
    category: str = "general"  # Category for grouping
    traits: Dict = field(default_factory=dict)  # Additional traits
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for EDSL."""
        return {
            "persona": self.persona,
            "background": self.background,
            "skepticism": self.skepticism,
            "category": self.category,
            **self.traits,
        }


@dataclass
class PersonaPack:
    """A collection of related personas."""
    
    name: str
    description: str
    personas: List[Persona]
    
    def get_personas(self, n: Optional[int] = None) -> List[Persona]:
        """Get personas, optionally limited to n."""
        if n is None:
            return self.personas
        return self.personas[:n]


# === DEVELOPER PERSONAS ===
DEVELOPER_PERSONAS = [
    Persona(
        persona="Senior software engineer using AI tools 4+ hours daily",
        background="Frustrated by rate limits, losing context, and managing git branches for AI tasks",
        skepticism="low",
        category="power_user"
    ),
    Persona(
        persona="Full-stack developer running multiple AI agents simultaneously",
        background="Uses Claude, GPT-4, and Gemini together. Constantly juggling terminals",
        skepticism="low",
        category="power_user"
    ),
    Persona(
        persona="AI-native developer building with AI assistance daily",
        background="Writes 80% of code with AI. Biggest pain is context switching",
        skepticism="low",
        category="power_user"
    ),
    Persona(
        persona="Developer who frequently hits API rate limits",
        background="Loses 2-3 hours per week waiting for rate limits to reset",
        skepticism="low",
        category="power_user"
    ),
    Persona(
        persona="Remote contractor working on multiple client projects",
        background="Needs to track costs per project and maintain separate contexts",
        skepticism="low",
        category="power_user"
    ),
    Persona(
        persona="Skeptical developer who prefers CLI tools",
        background="Doesn't see the point of wrapper tools, prefers minimal tooling",
        skepticism="high",
        category="skeptic"
    ),
    Persona(
        persona="Vim purist reluctantly using AI tools",
        background="Prefers terminal workflows, annoyed by Electron apps",
        skepticism="high",
        category="skeptic"
    ),
    Persona(
        persona="Security-conscious developer",
        background="Concerned about code being sent to external APIs, wants audit trails",
        skepticism="high",
        category="skeptic"
    ),
    Persona(
        persona="Junior developer excited about AI coding",
        background="New to AI-assisted coding, looking for intuitive tools",
        skepticism="low",
        category="junior"
    ),
    Persona(
        persona="Bootcamp graduate learning with AI",
        background="Relies heavily on AI for learning, needs clear UI",
        skepticism="low",
        category="junior"
    ),
]

# === MANAGER PERSONAS ===
MANAGER_PERSONAS = [
    Persona(
        persona="Tech lead managing team of 5 developers using AI tools",
        background="Wants to standardize workflows and track costs across the team",
        skepticism="medium",
        category="manager"
    ),
    Persona(
        persona="Startup CTO evaluating developer productivity tools",
        background="Needs to justify tool adoption to the team, values ROI",
        skepticism="medium",
        category="manager"
    ),
    Persona(
        persona="Engineering manager at 50-person startup",
        background="Concerned about AI tool sprawl, wants visibility into costs",
        skepticism="medium",
        category="manager"
    ),
    Persona(
        persona="VP of Engineering at enterprise company",
        background="Evaluating tools for 200+ developers. Cares about security and compliance",
        skepticism="high",
        category="manager"
    ),
    Persona(
        persona="Agency owner managing 10 developers",
        background="Needs to track AI costs per client project",
        skepticism="medium",
        category="manager"
    ),
]

# === COMMUNITY PERSONAS ===
COMMUNITY_PERSONAS = [
    Persona(
        persona="Open source enthusiast who stars useful repos",
        background="Has starred 500+ repos, values good documentation",
        skepticism="medium",
        category="community"
    ),
    Persona(
        persona="Hacker News regular",
        background="Has seen hundreds of dev tools, only stars truly novel projects",
        skepticism="high",
        category="community"
    ),
    Persona(
        persona="Dev influencer with large following",
        background="Always looking for interesting tools to share",
        skepticism="medium",
        category="community"
    ),
    Persona(
        persona="Open source maintainer",
        background="Uses AI for PR reviews and issue triage",
        skepticism="medium",
        category="community"
    ),
]

# === INDIE/ENTREPRENEUR PERSONAS ===
INDIE_PERSONAS = [
    Persona(
        persona="Indie developer building side projects",
        background="Juggles 3-4 projects, needs quick context-switching",
        skepticism="low",
        category="indie"
    ),
    Persona(
        persona="Solopreneur building multiple SaaS products",
        background="Values tools that remember state and reduce context loss",
        skepticism="low",
        category="indie"
    ),
    Persona(
        persona="Cost-conscious developer in developing country",
        background="Very cost-sensitive, needs to maximize value from every API call",
        skepticism="medium",
        category="cost_sensitive"
    ),
    Persona(
        persona="Freelancer billing $150/hour",
        background="Time is money, values any tool that saves time",
        skepticism="low",
        category="freelancer"
    ),
]

# === ENTERPRISE PERSONAS ===
ENTERPRISE_PERSONAS = [
    Persona(
        persona="DevOps engineer evaluating tools for engineering team",
        background="Cares about security, cost tracking, and Git integration",
        skepticism="high",
        category="devops"
    ),
    Persona(
        persona="Developer productivity lead at Fortune 500",
        background="Evaluating AI coding tools for 500+ developers",
        skepticism="high",
        category="enterprise"
    ),
    Persona(
        persona="Technical director at consulting firm",
        background="Needs tools that work across multiple client projects",
        skepticism="medium",
        category="enterprise"
    ),
]


# === PERSONA PACKS ===
PERSONA_PACKS = {
    "developers": PersonaPack(
        name="developers",
        description="Individual developers of various experience levels",
        personas=DEVELOPER_PERSONAS,
    ),
    "managers": PersonaPack(
        name="managers",
        description="Tech leads, CTOs, and engineering managers",
        personas=MANAGER_PERSONAS,
    ),
    "community": PersonaPack(
        name="community",
        description="Open source enthusiasts and influencers",
        personas=COMMUNITY_PERSONAS,
    ),
    "indie": PersonaPack(
        name="indie",
        description="Indie hackers, freelancers, and solopreneurs",
        personas=INDIE_PERSONAS,
    ),
    "enterprise": PersonaPack(
        name="enterprise",
        description="Enterprise and DevOps personas",
        personas=ENTERPRISE_PERSONAS,
    ),
    "mixed": PersonaPack(
        name="mixed",
        description="Balanced mix of all persona types",
        personas=DEVELOPER_PERSONAS + MANAGER_PERSONAS + COMMUNITY_PERSONAS + INDIE_PERSONAS,
    ),
    "skeptics": PersonaPack(
        name="skeptics",
        description="Skeptical personas for tough validation",
        personas=[p for p in DEVELOPER_PERSONAS + MANAGER_PERSONAS if p.skepticism == "high"],
    ),
}

# All personas combined
ALL_PERSONAS = (
    DEVELOPER_PERSONAS + 
    MANAGER_PERSONAS + 
    COMMUNITY_PERSONAS + 
    INDIE_PERSONAS + 
    ENTERPRISE_PERSONAS
)


def get_personas(
    pack: Optional[str] = None,
    categories: Optional[List[str]] = None,
    n: Optional[int] = None,
) -> List[Persona]:
    """
    Get personas based on pack or categories.
    
    Args:
        pack: Name of persona pack to use
        categories: Filter by categories
        n: Limit number of personas
    """
    if pack and pack in PERSONA_PACKS:
        personas = PERSONA_PACKS[pack].personas
    elif categories:
        personas = [p for p in ALL_PERSONAS if p.category in categories]
    else:
        personas = ALL_PERSONAS
    
    if n:
        personas = personas[:n]
    
    return personas


def get_balanced_personas(n: int = 10) -> List[Persona]:
    """Get a balanced sample of personas across categories."""
    
    # Group by category
    by_category = {}
    for p in ALL_PERSONAS:
        if p.category not in by_category:
            by_category[p.category] = []
        by_category[p.category].append(p)
    
    # Sample proportionally
    selected = []
    categories = list(by_category.keys())
    per_category = max(1, n // len(categories))
    
    for cat in categories:
        sample = random.sample(by_category[cat], min(per_category, len(by_category[cat])))
        selected.extend(sample)
    
    # Fill remaining slots randomly
    remaining = n - len(selected)
    if remaining > 0:
        available = [p for p in ALL_PERSONAS if p not in selected]
        selected.extend(random.sample(available, min(remaining, len(available))))
    
    return selected[:n]


def list_personas():
    """Print all available personas."""
    print(f"\nAvailable Personas ({len(ALL_PERSONAS)} total)")
    print("="*60)
    
    for pack_name, pack in PERSONA_PACKS.items():
        print(f"\n[{pack_name.upper()}] {pack.description} ({len(pack.personas)} personas)")
        for p in pack.personas[:3]:
            print(f"  • {p.persona[:50]}... (skepticism: {p.skepticism})")
        if len(pack.personas) > 3:
            print(f"  ... and {len(pack.personas) - 3} more")


if __name__ == "__main__":
    list_personas()
