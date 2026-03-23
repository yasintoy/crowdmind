"""
Multi-Metric EDSL Survey

Instead of just "would you star this?", asks:
- Interest (1-10)
- Usefulness (1-10)
- Urgency (1-10)
- Would Pay (Yes/Maybe/No)
- Reasoning (free text)
- Missing (free text)

Includes error handling for:
- Rate limits (exponential backoff)
- API timeouts (retry)
- Partial failures (continue with available results)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, TYPE_CHECKING
import time
import os

from crowdmind.validate.personas import get_balanced_personas, ALL_PERSONAS
from crowdmind.validate.runner import run_interviews, AdaptiveRunner

if TYPE_CHECKING:
    from edsl import AgentList, Survey

try:
    from edsl import Agent, AgentList, Survey, Model
    from edsl import QuestionLinearScale, QuestionMultipleChoice, QuestionFreeText
    HAS_EDSL = True
except ImportError:
    HAS_EDSL = False


# Error handling configuration
MAX_RETRIES = int(os.environ.get("CROWDMIND_MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = int(os.environ.get("CROWDMIND_RETRY_DELAY", "5"))
RATE_LIMIT_DELAY_SECONDS = int(os.environ.get("CROWDMIND_RATE_LIMIT_DELAY", "60"))


@dataclass
class PersonaFeedback:
    persona_name: str
    persona_category: str
    scores: Dict[str, Any]  # {"interest": 7, "usefulness": 6, ...}
    reasoning: str
    concerns: str
    missing: str


@dataclass
class ValidationResult:
    scores: Dict[str, float]  # Averaged scores: {"interest": 6.5, "usefulness": 7.2}
    would_pay: Dict[str, float]  # {"yes": 0.3, "maybe": 0.4, "no": 0.3}
    feedback: List[PersonaFeedback]
    synthesis: str  # AI-generated summary
    recommendations: List[str]
    raw_results: Any = None


def create_survey(content: str, context_prompt: str = "") -> "Survey":
    """Create EDSL survey with multiple metrics"""
    if not HAS_EDSL:
        raise ImportError("EDSL required")

    base_prompt = f"""{context_prompt}

IDEA/PRODUCT TO EVALUATE:
---
{content[:2000]}
---
"""

    return Survey([
        QuestionLinearScale(
            question_name="interest",
            question_text=f"""{base_prompt}

How interested are you in this? (1 = Not at all, 10 = Extremely interested)""",
            question_options=list(range(1, 11))
        ),
        QuestionLinearScale(
            question_name="usefulness",
            question_text=f"""{base_prompt}

How useful would this be for your daily work? (1 = Not useful, 10 = Extremely useful)""",
            question_options=list(range(1, 11))
        ),
        QuestionLinearScale(
            question_name="urgency",
            question_text=f"""{base_prompt}

How urgently do you need this problem solved? (1 = Not urgent, 10 = Critical)""",
            question_options=list(range(1, 11))
        ),
        QuestionMultipleChoice(
            question_name="would_pay",
            question_text=f"""{base_prompt}

Would you pay for this?""",
            question_options=["Yes, definitely", "Maybe, depends on price", "No"]
        ),
        QuestionFreeText(
            question_name="reasoning",
            question_text=f"""{base_prompt}

Explain your scores in 2-3 sentences. What drove your ratings?"""
        ),
        QuestionFreeText(
            question_name="missing",
            question_text=f"""{base_prompt}

What would make this more appealing? What's missing?"""
        ),
    ])


def _run_with_retry(func, verbose: bool = True, max_retries: int = MAX_RETRIES):
    """
    Run a function with retry logic for rate limits and transient errors.
    
    Handles:
    - Rate limits (429): Wait 60s and retry
    - Timeouts: Exponential backoff
    - Transient API errors: Retry up to max_retries
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Check for rate limit errors
            if "429" in error_str or (
                "rate" in error_str and "limit" in error_str
            ):
                if verbose:
                    print(f"  ⚠️  Rate limit hit. Waiting {RATE_LIMIT_DELAY_SECONDS}s before retry...")
                time.sleep(RATE_LIMIT_DELAY_SECONDS)
                continue
            
            # Check for timeout errors
            if "timeout" in error_str or "timed out" in error_str:
                delay = RETRY_DELAY_SECONDS * (2 ** attempt)  # Exponential backoff
                if verbose:
                    print(f"  ⚠️  Timeout. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                continue
            
            # Check for transient API errors
            if "500" in error_str or "502" in error_str or "503" in error_str:
                delay = RETRY_DELAY_SECONDS * (2 ** attempt)
                if verbose:
                    print(f"  ⚠️  API error. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                continue
            
            # Unknown error - don't retry
            raise
    
    # All retries exhausted
    raise last_error


def _summarize_edsl_exceptions(results: Any) -> str:
    """
    Human-readable summary when EDSL interviews partially fail.
    Replaces EDSL's stderr-only 'Exceptions were raised.' + HTML report path.
    """
    if not getattr(results, "has_unfixed_exceptions", False):
        return ""
    rate_limit = False
    timeout = False
    auth_error = False
    other_msgs: List[str] = []
    th = getattr(results, "task_history", None)
    if th is None:
        return (
            "\n⚠️  CrowdMind: some persona interviews failed.\n"
            "   Common cause: Anthropic rate limits (429) from parallel requests.\n"
            "   Fix: use --personas 3–5 or wait 60s and retry."
        )
    try:
        exc_groups = getattr(th, "exceptions", None) or []
        for coll in exc_groups:
            if hasattr(coll, "list"):
                for item in coll.list():
                    et = str(item.get("exception_type", ""))
                    if "RateLimit" in et:
                        rate_limit = True
                    if "Timeout" in et:
                        timeout = True
                    if "Authentication" in et or "Auth" in et:
                        auth_error = True
            raw = getattr(coll, "data", None)
            if raw is not None and hasattr(raw, "items"):
                for _q, entries in raw.items():
                    for entry in entries:
                        exc = getattr(entry, "exception", None)
                        if exc is None:
                            continue
                        msg = str(exc).lower()
                        if "429" in msg or "rate_limit" in msg:
                            rate_limit = True
                        if "timeout" in msg:
                            timeout = True
                        if "401" in msg or "403" in msg or "api key" in msg:
                            auth_error = True
                        snippet = str(exc)[:200].replace("\n", " ")
                        if snippet and snippet not in other_msgs:
                            other_msgs.append(snippet)
    except Exception:
        pass

    lines = [
        "\n⚠️  CrowdMind: not all persona interviews completed successfully "
        "(scores may be skewed)."
    ]
    if rate_limit:
        lines.append(
            "   Cause: API rate limits — too many parallel model calls (common on Anthropic)."
        )
        lines.append(
            "   Fix:  use --personas 3–5, wait ~60s between runs, or upgrade API limits."
        )
    elif auth_error:
        lines.append("   Cause: API authentication / permission error.")
        lines.append("   Fix:  check ANTHROPIC_API_KEY (or your provider key) and billing.")
    elif timeout:
        lines.append("   Cause: Request timeouts.")
        lines.append("   Fix:  retry with fewer personas or later.")
    elif other_msgs:
        lines.append(f"   Detail: {other_msgs[0]}")
    else:
        lines.append("   Cause: LLM or EDSL errors during some interviews.")
        lines.append("   Fix:  retry with --personas 5; confirm API quota and model name.")
    return "\n".join(lines)


def run_multi_metric_survey(
    content: str,
    context_prompt: str = "",
    agents: Optional["AgentList"] = None,
    num_agents: int = 10,
    model_name: str = "claude-sonnet-4-20250514",
    verbose: bool = True,
    max_retries: int = MAX_RETRIES,
    report_api_issues: bool = True,
    runner: Optional[AdaptiveRunner] = None,  # NEW
) -> ValidationResult:
    """
    Run the multi-metric survey and return structured results.
    
    Includes automatic retry for:
    - Rate limits (waits 60s)
    - Timeouts (exponential backoff)
    - Transient API errors (up to max_retries)
    
    Args:
        content: The idea/product to evaluate
        context_prompt: Product context for better evaluation
        agents: Pre-built EDSL AgentList (optional)
        num_agents: Number of personas to use (if agents not provided)
        model_name: LLM model to use
        verbose: Print progress
        max_retries: Max retry attempts for transient errors
        report_api_issues: If True, print a clear message when some interviews fail
            (even when verbose=False; use False for --quiet CLI)
    """
    if not HAS_EDSL:
        raise ImportError("EDSL required. Install with: pip install edsl")

    from dotenv import load_dotenv
    load_dotenv()

    # Create agents if not provided
    personas_list = []
    if agents is None:
        personas_list = get_balanced_personas(num_agents) if num_agents else ALL_PERSONAS[:10]
        agents = AgentList([Agent(traits=p.to_dict()) for p in personas_list])
    
    # Get agent count - try different attributes for compatibility
    try:
        agent_count = len(agents)
    except:
        agent_count = num_agents

    # Create survey
    survey = create_survey(content, context_prompt)
    model = Model(model_name)

    if verbose:
        print(f"Running multi-metric survey with {agent_count} personas...")
        estimated_cost = agent_count * 0.01  # ~$0.01 per persona
        print(f"  Estimated cost: ~${estimated_cost:.2f}")

    # Question names to extract
    question_names = [
        "interest", "usefulness", "urgency",
        "would_pay", "reasoning", "missing",
    ]

    # Run with adaptive concurrency (per-interview, with retry)
    agents_list = list(agents) if not isinstance(agents, list) else agents
    raw_results = run_interviews(
        survey=survey,
        agents=agents_list,
        model=model,
        question_names=question_names,
        verbose=verbose,
        runner=runner,
        max_retries=max_retries,
    )

    # Filter out failed interviews (None entries)
    successful = [(i, r) for i, r in enumerate(raw_results) if r is not None]
    failed_count = len(raw_results) - len(successful)

    if report_api_issues and failed_count > 0:
        print(
            f"\n  Warning: {failed_count} of {len(raw_results)} persona "
            f"interviews failed. Scores based on {len(successful)} responses."
        )

    # Extract scores from per-agent result dicts
    interest_scores = [r.get("interest") for _, r in successful if r.get("interest") is not None]
    usefulness_scores = [r.get("usefulness") for _, r in successful if r.get("usefulness") is not None]
    urgency_scores = [r.get("urgency") for _, r in successful if r.get("urgency") is not None]
    would_pay_responses = [r.get("would_pay") for _, r in successful if r.get("would_pay") is not None]
    reasoning_responses = [r.get("reasoning") for _, r in successful if r.get("reasoning") is not None]
    missing_responses = [r.get("missing") for _, r in successful if r.get("missing") is not None]

    # Calculate averages
    def avg(lst: List) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    scores = {
        "interest": round(avg(interest_scores), 1),
        "usefulness": round(avg(usefulness_scores), 1),
        "urgency": round(avg(urgency_scores), 1),
        "overall": round((avg(interest_scores) + avg(usefulness_scores) + avg(urgency_scores)) / 3, 1)
    }

    # Calculate would_pay distribution
    total_pay = len(would_pay_responses)
    would_pay = {
        "yes": round(would_pay_responses.count("Yes, definitely") / total_pay, 2) if total_pay else 0,
        "maybe": round(would_pay_responses.count("Maybe, depends on price") / total_pay, 2) if total_pay else 0,
        "no": round(would_pay_responses.count("No") / total_pay, 2) if total_pay else 0,
    }

    # Build feedback list (only for successful interviews)
    feedback = []
    for orig_idx, r in successful:
        if personas_list and orig_idx < len(personas_list):
            persona = personas_list[orig_idx]
            persona_label = (
                persona.name if hasattr(persona, 'name')
                else persona.persona if hasattr(persona, 'persona')
                else f"Persona {orig_idx+1}"
            )
            persona_cat = persona.category if hasattr(persona, 'category') else "unknown"
        else:
            persona_label = f"Persona {orig_idx+1}"
            persona_cat = "unknown"

        feedback.append(PersonaFeedback(
            persona_name=persona_label,
            persona_category=persona_cat,
            scores={
                "interest": r.get("interest"),
                "usefulness": r.get("usefulness"),
                "urgency": r.get("urgency"),
            },
            reasoning=r.get("reasoning", ""),
            concerns="",
            missing=r.get("missing", ""),
        ))

    # Generate synthesis (simple version - could use LLM)
    synthesis = _generate_synthesis(scores, would_pay, feedback)
    recommendations = _generate_recommendations(scores, would_pay, feedback)

    return ValidationResult(
        scores=scores,
        would_pay=would_pay,
        feedback=feedback,
        synthesis=synthesis,
        recommendations=recommendations,
        raw_results=raw_results
    )


def _generate_synthesis(scores: Dict, would_pay: Dict, feedback: List) -> str:
    """Generate a synthesis of the results"""
    overall = scores.get("overall", 5)

    if overall >= 7:
        sentiment = "strong positive"
    elif overall >= 5:
        sentiment = "moderate"
    else:
        sentiment = "weak"

    pay_pct = int(would_pay.get("yes", 0) * 100 + would_pay.get("maybe", 0) * 50)

    return f"""Overall reception: {sentiment} ({scores['overall']}/10)
Interest: {scores['interest']}/10 | Usefulness: {scores['usefulness']}/10 | Urgency: {scores['urgency']}/10
Payment intent: {pay_pct}% would consider paying"""


def _generate_recommendations(scores: Dict, would_pay: Dict, feedback: List) -> List[str]:
    """Generate recommendations based on results"""
    recs = []

    if scores.get("urgency", 5) < 4:
        recs.append("Low urgency - consider if this is really needed now")

    if scores.get("interest", 5) >= 7 and scores.get("usefulness", 5) < 5:
        recs.append("High interest but low usefulness - may be 'shiny object syndrome'")

    if would_pay.get("no", 0) > 0.5:
        recs.append("Majority won't pay - consider freemium or open source model")

    if would_pay.get("yes", 0) > 0.3:
        recs.append("Strong payment intent - worth building")

    # Extract common themes from missing
    missing_texts = [f.missing for f in feedback if f.missing]
    if missing_texts:
        recs.append("Common requests: review feedback for feature ideas")

    return recs if recs else ["No specific recommendations - scores are moderate"]
