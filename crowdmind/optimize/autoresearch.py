"""
Karpathy-style Autoresearch Loop

Iteratively improves content by:
1. Proposing improvements (using LLM)
2. Testing with EDSL personas
3. Keeping improvements that score better
4. Discarding those that don't help
"""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, List

try:
    from anthropic import Anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def _run_survey(
    content: str,
    context_prompt: str,
    num_agents: int,
    verbose: bool,
) -> Any:
    try:
        from crowdmind.validate.survey import run_multi_metric_survey

        return run_multi_metric_survey(
            content,
            context_prompt,
            num_agents=num_agents,
            verbose=verbose,
        )
    except ImportError:
        from crowdmind.validate.panel import run_evaluation

        eval_content = content
        if context_prompt:
            eval_content = (
                f"CONTEXT FOR EVALUATION:\n{context_prompt}\n\n---\n\n{content}"
            )
        r = run_evaluation(
            readme_content=eval_content,
            verbose=verbose,
            num_agents=num_agents,
        )
        avg = float(r.get("avg_star", 5))
        scores = {
            "overall": avg,
            "interest": avg,
            "usefulness": avg,
            "urgency": avg,
        }
        return SimpleNamespace(scores=scores)


@dataclass
class Iteration:
    number: int
    proposal: str
    before_score: float
    after_score: float
    kept: bool
    content_before: str
    content_after: str


@dataclass
class OptimizationResult:
    final_content: str
    final_score: float
    initial_score: float
    iterations: int
    history: List[Iteration]
    improvements_made: List[str]
    target_reached: bool


class AutoresearchLoop:
    """Implements the autoresearch optimization loop"""

    def __init__(self, model_name: str = "claude-sonnet-4-20250514"):
        self.model_name = model_name
        if HAS_ANTHROPIC:
            self.client = Anthropic()
        else:
            self.client = None

    def optimize(
        self,
        content: str,
        context_prompt: str = "",
        target_score: float = 80.0,
        max_iterations: int = 10,
        metric: str = "overall",
        verbose: bool = True,
        num_personas: int = 10,
    ) -> OptimizationResult:
        """
        Run the autoresearch optimization loop.

        Args:
            content: The content to optimize (README, pitch, etc.)
            context_prompt: Product context for evaluation
            target_score: Stop when this score is reached (0-100 scale)
            max_iterations: Maximum optimization attempts
            metric: Which metric to optimize ("overall", "interest", "usefulness", "urgency")
            verbose: Print progress
            num_personas: Number of personas for each evaluation

        Returns:
            OptimizationResult with final content, score, and history
        """
        history: List[Iteration] = []
        current_content = content
        improvements_made: List[str] = []

        if verbose:
            print("Initial evaluation...")

        initial_result = _run_survey(
            current_content,
            context_prompt,
            num_agents=num_personas,
            verbose=False,
        )
        current_score = float(initial_result.scores.get(metric, 5)) * 10
        initial_score = current_score

        if verbose:
            print(f"Initial score: {current_score:.1f}/100")
            print(f"Target: {target_score}/100")
            print()

        for i in range(max_iterations):
            if current_score >= target_score:
                if verbose:
                    print("✓ Target reached!")
                break

            if verbose:
                print(f"Iteration {i + 1}/{max_iterations}...")

            proposal = self._propose_improvement(
                current_content,
                context_prompt,
                current_score,
                [h.proposal for h in history if not h.kept],
            )

            if verbose:
                print(f"  Proposal: {proposal[:60]}...")

            new_content = self._apply_proposal(current_content, proposal)

            new_result = _run_survey(
                new_content,
                context_prompt,
                num_agents=num_personas,
                verbose=False,
            )
            new_score = float(new_result.scores.get(metric, 5)) * 10

            kept = new_score > current_score

            iteration = Iteration(
                number=i + 1,
                proposal=proposal,
                before_score=current_score,
                after_score=new_score,
                kept=kept,
                content_before=current_content,
                content_after=new_content,
            )
            history.append(iteration)

            if kept:
                current_content = new_content
                current_score = new_score
                improvements_made.append(proposal)
                if verbose:
                    print(
                        f"  ✓ Kept: {current_score:.1f}/100 (+{new_score - iteration.before_score:.1f})"
                    )
            else:
                if verbose:
                    print(f"  ✗ Discarded: {new_score:.1f}/100 (no improvement)")

            if verbose:
                print()

        return OptimizationResult(
            final_content=current_content,
            final_score=current_score,
            initial_score=initial_score,
            iterations=len(history),
            history=history,
            improvements_made=improvements_made,
            target_reached=current_score >= target_score,
        )

    def _propose_improvement(
        self,
        content: str,
        context: str,
        current_score: float,
        failed_proposals: List[str],
    ) -> str:
        """Use LLM to propose an improvement"""
        if not self.client:
            return "Add more concrete examples and social proof"

        failed_str = ""
        if failed_proposals:
            failed_str = f"""

These proposals were already tried and didn't improve the score:
{chr(10).join(f'- {p}' for p in failed_proposals[-5:])}

Propose something different."""

        prompt = f"""You are an expert at improving product descriptions and README files.

Current content has a score of {current_score:.0f}/100. Goal is to improve it.

{context}

Current content:
---
{content[:3000]}
---
{failed_str}

Propose ONE specific, actionable improvement to increase the appeal. Be concrete.
Examples of good proposals:
- "Add a one-line description at the top that explains the core value"
- "Add a quick-start code example in the first 30 seconds"
- "Add social proof (users, stars, testimonials)"
- "Simplify the installation instructions"
- "Lead with the problem before the solution"

Respond with just the improvement proposal (1-2 sentences):"""

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()

    def _apply_proposal(self, content: str, proposal: str) -> str:
        """Use LLM to apply the proposed improvement"""
        if not self.client:
            return content + f"\n\n<!-- Proposed: {proposal} -->"

        prompt = f"""Apply this improvement to the content.

Improvement to make:
{proposal}

Current content:
---
{content}
---

Return the improved content. Make minimal changes - just apply the specific improvement.
Do not add explanatory comments. Just return the improved content:"""

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()


def run_optimization(
    content: str,
    context_prompt: str = "",
    target: float = 80.0,
    max_iterations: int = 10,
    verbose: bool = True,
) -> OptimizationResult:
    """Convenience function to run optimization"""
    loop = AutoresearchLoop()
    return loop.optimize(
        content=content,
        context_prompt=context_prompt,
        target_score=target,
        max_iterations=max_iterations,
        verbose=verbose,
    )
