"""
EDSL-based Validation Panel

Uses AI agents as simulated target users to evaluate
product ideas through structured surveys.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Union

from crowdmind.config import get_config
from crowdmind.validate.personas import (
    Persona,
    get_personas,
    get_balanced_personas,
    ALL_PERSONAS,
)

try:
    from edsl import Agent, AgentList, Model, Survey
    from edsl import QuestionLinearScale, QuestionMultipleChoice, QuestionFreeText
    HAS_EDSL = True
except ImportError:
    HAS_EDSL = False

from crowdmind.validate.runner import run_interviews


def create_agents(
    n: Optional[int] = None,
    pack: Optional[str] = None,
    categories: Optional[List[str]] = None,
    balanced: bool = True,
) -> "AgentList":
    """
    Create list of AI agents with different personas.
    
    Args:
        n: Number of agents (default: all)
        pack: Persona pack name
        categories: Filter by category
        balanced: If True and n specified, sample proportionally
    """
    if not HAS_EDSL:
        raise ImportError("EDSL is required for validation. Install with: pip install edsl")
    
    if pack:
        personas = get_personas(pack=pack, n=n)
    elif categories:
        personas = get_personas(categories=categories, n=n)
    elif n and balanced:
        personas = get_balanced_personas(n)
    elif n:
        personas = ALL_PERSONAS[:n]
    else:
        personas = ALL_PERSONAS
    
    return AgentList([
        Agent(traits=p.to_dict()) for p in personas
    ])


def create_star_question(content: str) -> "QuestionLinearScale":
    """Create star likelihood question with content embedded."""
    if not HAS_EDSL:
        raise ImportError("EDSL is required")
    
    # Truncate content for reliability
    content_excerpt = content[:3000]
    
    return QuestionLinearScale(
        question_name="star",
        question_text=f"""After reading this product description, how likely would you be to star/recommend this?

PRODUCT:
---
{content_excerpt}
---

Rate from 1-10 where 1 = "Definitely would NOT recommend" and 10 = "Definitely WOULD recommend".""",
        question_options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    )


def create_ab_star_question(content: str, version: str) -> "QuestionLinearScale":
    """Create star question for A/B test."""
    if not HAS_EDSL:
        raise ImportError("EDSL is required")
    
    content_excerpt = content[:3000]
    
    return QuestionLinearScale(
        question_name=f"star_{version.lower()}",
        question_text=f"""Rate this product description (Version {version}).

PRODUCT:
---
{content_excerpt}
---

How likely would you be to recommend this? (1-10)""",
        question_options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    )


def run_evaluation(
    readme_content: Optional[str] = None,
    project_path: Optional[Union[str, Path]] = None,
    verbose: bool = True,
    num_agents: Optional[int] = None,
    pack: Optional[str] = None,
    categories: Optional[List[str]] = None,
    balanced: bool = True,
    model_name: Optional[str] = None,
) -> Dict:
    """
    Run evaluation with agent personas.
    
    Args:
        readme_content: Content to evaluate
        project_path: Path to project (will read README.md)
        verbose: Print progress
        num_agents: Number of agents to use
        pack: Persona pack name
        categories: Filter personas by category
        balanced: Sample proportionally across categories
        model_name: LLM model to use
    
    Returns dict with:
    - star_rate: percentage of agents who scored >= 7
    - avg_star: average star likelihood (1-10)
    - scores: individual scores from each agent
    - by_category: breakdown by persona category
    """
    if not HAS_EDSL:
        raise ImportError("EDSL is required for validation. Install with: pip install edsl")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get content
    if readme_content is None:
        if project_path:
            project_path = Path(project_path)
            readme_path = project_path / "README.md" if project_path.is_dir() else project_path
            if readme_path.exists():
                readme_content = readme_path.read_text()
    
    if not readme_content:
        return {"error": "No content to evaluate"}
    
    # Get config
    config = get_config()
    if model_name is None:
        model_name = config.default_model
    
    # Create agents and model
    agents = create_agents(n=num_agents, pack=pack, categories=categories, balanced=balanced)
    question = create_star_question(readme_content)
    model = Model(model_name)
    
    agent_count = len(agents._agents) if hasattr(agents, '_agents') else num_agents or len(ALL_PERSONAS)
    
    if verbose:
        print(f"Running evaluation with {agent_count} agent personas...")
        if pack:
            print(f"  Pack: {pack}")
        if categories:
            print(f"  Categories: {categories}")
    
    # Run the question with all agents via AdaptiveRunner
    survey = Survey([question])
    agents_list = agents._agents if hasattr(agents, '_agents') else list(agents)
    raw_results = run_interviews(
        survey=survey,
        agents=agents_list,
        model=model,
        question_names=["star"],
        verbose=verbose,
    )
    star_scores = [
        r.get("star") for r in raw_results
        if r is not None and r.get("star") is not None
    ]
    
    # Calculate metrics
    star_rate = len([s for s in star_scores if s >= 7]) / len(star_scores) if star_scores else 0
    avg_star = sum(star_scores) / len(star_scores) if star_scores else 0
    
    # Category breakdown
    by_category = {}
    try:
        personas_used = agents._agents if hasattr(agents, '_agents') else []
        for i, score in enumerate(star_scores):
            if i < len(personas_used):
                cat = personas_used[i].traits.get('category', 'other')
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(score)
    except Exception:
        pass
    
    result = {
        "star_rate": round(star_rate * 100, 1),
        "avg_star": round(avg_star, 2),
        "total_score": round(avg_star * 10, 1),  # 0-100 scale
        "agents_evaluated": len(star_scores),
        "scores": star_scores,
        "by_category": {k: {"avg": round(sum(v)/len(v), 2), "scores": v} for k, v in by_category.items()} if by_category else {},
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print("VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Agents Evaluated: {result['agents_evaluated']}")
        print(f"Star Rate (>=7/10): {result['star_rate']}%")
        print(f"Avg Star Likelihood: {result['avg_star']}/10")
        print(f"Total Score: {result['total_score']}/100")
        
        if result['by_category']:
            print(f"\nBy Category:")
            for cat, data in sorted(result['by_category'].items(), key=lambda x: x[1]['avg'], reverse=True):
                print(f"  {cat}: {data['avg']}/10 (n={len(data['scores'])})")
        
        print(f"\nIndividual scores: {star_scores}")
    
    return result


def run_ab_test(
    content_a: str,
    content_b: str,
    change_description: str,
    verbose: bool = True,
    num_agents: Optional[int] = None,
    pack: Optional[str] = None,
    categories: Optional[List[str]] = None,
    model_name: Optional[str] = None,
) -> Dict:
    """
    Run A/B test comparing two content versions.
    
    Args:
        content_a: Current version
        content_b: Proposed version
        change_description: What changed
        verbose: Print progress
        num_agents: Number of agents
        pack: Persona pack
        categories: Filter by category
        model_name: LLM model to use
    
    Returns dict with:
    - winner: "A" or "B" or "TIE"
    - a_score: average score for version A
    - b_score: average score for version B
    - delta: B - A (positive means B is better)
    - significant: whether the difference is meaningful (>0.5 points)
    """
    if not HAS_EDSL:
        raise ImportError("EDSL is required for validation. Install with: pip install edsl")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    config = get_config()
    if model_name is None:
        model_name = config.default_model
    
    agents = create_agents(n=num_agents, pack=pack, categories=categories)
    model = Model(model_name)
    
    agent_count = len(agents._agents) if hasattr(agents, '_agents') else num_agents or len(ALL_PERSONAS)
    
    if verbose:
        print(f"Running A/B test: {change_description}")
        print(f"Testing with {agent_count} agent personas...")
    
    agents_list = agents._agents if hasattr(agents, '_agents') else list(agents)

    # Run version A
    q_a = create_ab_star_question(content_a, "A")
    survey_a = Survey([q_a])
    raw_a = run_interviews(
        survey=survey_a,
        agents=agents_list,
        model=model,
        question_names=["star_a"],
        verbose=verbose,
    )
    a_scores = [
        r.get("star_a") for r in raw_a
        if r is not None and r.get("star_a") is not None
    ]

    # Run version B
    q_b = create_ab_star_question(content_b, "B")
    survey_b = Survey([q_b])
    raw_b = run_interviews(
        survey=survey_b,
        agents=agents_list,
        model=model,
        question_names=["star_b"],
        verbose=verbose,
    )
    b_scores = [
        r.get("star_b") for r in raw_b
        if r is not None and r.get("star_b") is not None
    ]
    
    # Calculate averages
    a_avg = sum(a_scores) / len(a_scores) if a_scores else 0
    b_avg = sum(b_scores) / len(b_scores) if b_scores else 0
    
    delta = b_avg - a_avg
    winner = "B" if delta > 0.3 else "A" if delta < -0.3 else "TIE"
    significant = abs(delta) >= 0.5
    
    result = {
        "winner": winner,
        "a_score": round(a_avg, 2),
        "b_score": round(b_avg, 2),
        "delta": round(delta, 2),
        "significant": significant,
        "a_scores": a_scores,
        "b_scores": b_scores,
        "agents_evaluated": len(a_scores),
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print("A/B TEST RESULTS")
        print(f"{'='*60}")
        print(f"Agents: {agent_count}")
        print(f"Version A (current): {result['a_score']}/10")
        print(f"Version B (proposed): {result['b_score']}/10")
        print(f"Delta: {result['delta']:+.2f}")
        print(f"Winner: {result['winner']} {'(significant)' if significant else '(not significant)'}")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate product with AI personas")
    parser.add_argument("path", nargs="?", help="Path to README or project")
    parser.add_argument("--content", help="Direct content to evaluate")
    parser.add_argument("--agents", type=int, default=None, help="Number of agents")
    parser.add_argument("--pack", help="Persona pack")
    parser.add_argument("--categories", nargs="+", help="Persona categories")
    parser.add_argument("--ab-test", action="store_true", help="Run A/B test")
    parser.add_argument("--output", help="Output file (JSON)")
    args = parser.parse_args()
    
    if args.content:
        content = args.content
    elif args.path:
        content = Path(args.path).read_text()
    else:
        print("Please provide content via --content or path argument")
        exit(1)
    
    result = run_evaluation(
        readme_content=content,
        num_agents=args.agents,
        pack=args.pack,
        categories=args.categories,
    )
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to {args.output}")
