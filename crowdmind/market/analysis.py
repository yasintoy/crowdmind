"""
Market Analysis Agent

Analyzes:
- Who would pay for this product (buyer personas)
- How much they'd pay (pricing analysis)
- How to sell (go-to-market)
- Success predictions (stars, users, revenue potential)

Uses EDSL to survey simulated buyers on willingness to pay.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict, Union
from datetime import datetime

from crowdmind.config import get_config
from crowdmind.validate.runner import run_interviews, AdaptiveRunner

try:
    from edsl import Agent, AgentList, Model
    from edsl import QuestionLinearScale, QuestionMultipleChoice, QuestionFreeText
    HAS_EDSL = True
except ImportError:
    HAS_EDSL = False


# Buyer personas (different from user personas - these are BUYERS)
BUYER_PERSONAS = [
    # Individual Buyers
    {
        "persona": "Senior developer spending $100+/month on AI tools",
        "role": "individual_contributor",
        "company_size": "any",
        "budget_authority": "personal",
        "current_spend": "$100-200/month",
        "pain_level": "high",
    },
    {
        "persona": "Freelance developer billing $150/hour",
        "role": "freelancer",
        "company_size": "solo",
        "budget_authority": "full",
        "current_spend": "$50-100/month",
        "pain_level": "high",
    },
    {
        "persona": "Indie hacker building SaaS products",
        "role": "founder",
        "company_size": "1-5",
        "budget_authority": "full",
        "current_spend": "$200-500/month",
        "pain_level": "medium",
    },
    
    # Team Buyers (SMB)
    {
        "persona": "Tech lead at 20-person startup",
        "role": "tech_lead",
        "company_size": "10-50",
        "budget_authority": "team_budget",
        "current_spend": "$500-2000/month",
        "pain_level": "high",
    },
    {
        "persona": "CTO at seed-stage startup (5 engineers)",
        "role": "cto",
        "company_size": "5-20",
        "budget_authority": "full",
        "current_spend": "$1000-3000/month",
        "pain_level": "medium",
    },
    {
        "persona": "Engineering manager at Series A startup",
        "role": "eng_manager",
        "company_size": "20-100",
        "budget_authority": "department_budget",
        "current_spend": "$5000-15000/month",
        "pain_level": "medium",
    },
    
    # Enterprise Buyers
    {
        "persona": "VP of Engineering at 500-person company",
        "role": "vp_eng",
        "company_size": "200-1000",
        "budget_authority": "large_budget",
        "current_spend": "$50k-200k/year",
        "pain_level": "low",
    },
    {
        "persona": "Developer productivity lead at Fortune 500",
        "role": "dev_productivity",
        "company_size": "1000+",
        "budget_authority": "initiative_budget",
        "current_spend": "$500k+/year",
        "pain_level": "low",
    },
    
    # Agency/Consultancy
    {
        "persona": "Owner of 15-person dev agency",
        "role": "agency_owner",
        "company_size": "10-50",
        "budget_authority": "full",
        "current_spend": "$3000-10000/month",
        "pain_level": "high",
    },
    {
        "persona": "Technical director at consulting firm",
        "role": "tech_director",
        "company_size": "50-200",
        "budget_authority": "project_budgets",
        "current_spend": "$10k-50k/month",
        "pain_level": "medium",
    },
]


def read_project_readme(project_path: Union[str, Path]) -> str:
    """Read project README."""
    project_path = Path(project_path)
    readme_path = project_path / "README.md" if project_path.is_dir() else project_path
    if readme_path.exists():
        return readme_path.read_text()[:3000]
    return ""


def run_market_survey(
    product_description: str,
    verbose: bool = True,
    model_name: Optional[str] = None,
) -> Dict:
    """Run willingness-to-pay survey with buyer personas."""
    
    if not HAS_EDSL:
        raise ImportError("EDSL is required. Install with: pip install edsl")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    config = get_config()
    if model_name is None:
        model_name = config.default_model
    
    agents = AgentList([Agent(traits=p) for p in BUYER_PERSONAS])
    model = Model(model_name)
    
    if verbose:
        print(f"Running market survey with {len(BUYER_PERSONAS)} buyer personas...")
    
    results = {
        "would_pay": [],
        "price_points": [],
        "triggers": [],
        "objections": [],
        "by_segment": {},
    }
    
    # Run willingness to pay question
    q_pay = QuestionLinearScale(
        question_name="would_pay",
        question_text=f"""You are evaluating this product for potential purchase.

PRODUCT:
{product_description}

How likely are you to pay for this tool? (1 = Never, 10 = Definitely)""",
        question_options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    )
    
    # Create shared runner (concurrency state persists between surveys)
    from edsl import Survey
    runner = AdaptiveRunner(max_concurrency=5, verbose=verbose)
    agents_list = list(agents) if not isinstance(agents, list) else agents

    # Run willingness-to-pay
    pay_survey = Survey([q_pay])
    pay_raw = runner.run(pay_survey, agents_list, model, question_names=["would_pay"])
    results["would_pay"] = [
        r.get("would_pay") for r in pay_raw
        if r is not None and r.get("would_pay") is not None
    ]

    # Cooldown between surveys
    cooldown = runner.get_cooldown()
    if cooldown > 0:
        if verbose:
            print(f"  Cooling down {cooldown:.0f}s before next survey...")
        time.sleep(cooldown)

    # Run price point question
    q_price = QuestionMultipleChoice(
        question_name="price_point",
        question_text=f"""For this product, what's the MAXIMUM you would pay per user per month?

PRODUCT SUMMARY: {product_description[:500]}...

Select your maximum price:""",
        question_options=[
            "$0 - Only if free",
            "$5-10/month",
            "$10-20/month",
            "$20-50/month",
            "$50-100/month",
            "$100+/month"
        ]
    )

    # Run price-point
    price_survey = Survey([q_price])
    price_raw = runner.run(price_survey, agents_list, model, question_names=["price_point"])
    results["price_points"] = [
        r.get("price_point") for r in price_raw
        if r is not None and r.get("price_point") is not None
    ]
    
    # Calculate segment breakdown
    for i, persona in enumerate(BUYER_PERSONAS):
        segment = persona.get("company_size", "unknown")
        if segment not in results["by_segment"]:
            results["by_segment"][segment] = {"would_pay": [], "price_points": []}
        
        if i < len(results["would_pay"]):
            results["by_segment"][segment]["would_pay"].append(results["would_pay"][i])
        if i < len(results["price_points"]):
            results["by_segment"][segment]["price_points"].append(results["price_points"][i])
    
    return results


def run_success_prediction(
    product_description: str,
    verbose: bool = True,
    model_name: Optional[str] = None,
) -> Dict:
    """Predict product success metrics."""
    
    if not HAS_EDSL:
        raise ImportError("EDSL is required. Install with: pip install edsl")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    config = get_config()
    if model_name is None:
        model_name = config.default_model
    
    agents = AgentList([Agent(traits=p) for p in BUYER_PERSONAS])
    model = Model(model_name)
    
    if verbose:
        print(f"Running success prediction with {len(BUYER_PERSONAS)} personas...")
    
    # Star prediction
    q_stars = QuestionMultipleChoice(
        question_name="star_estimate",
        question_text=f"""Based on this product, estimate realistic GitHub stars in 1 year:

PRODUCT: {product_description[:500]}...

Your estimate:""",
        question_options=[
            "< 500 stars",
            "500 - 1,000 stars",
            "1,000 - 3,000 stars",
            "3,000 - 5,000 stars",
            "5,000 - 10,000 stars",
            "10,000+ stars"
        ]
    )
    
    from edsl import Survey
    runner = AdaptiveRunner(max_concurrency=5, verbose=verbose)
    agents_list = list(agents) if not isinstance(agents, list) else agents

    # Star prediction
    star_survey = Survey([q_stars])
    star_raw = runner.run(star_survey, agents_list, model, question_names=["star_estimate"])
    star_estimates = [
        r.get("star_estimate") for r in star_raw
        if r is not None and r.get("star_estimate") is not None
    ]

    cooldown = runner.get_cooldown()
    if cooldown > 0:
        if verbose:
            print(f"  Cooling down {cooldown:.0f}s...")
        time.sleep(cooldown)

    # User prediction
    q_users = QuestionMultipleChoice(
        question_name="user_estimate",
        question_text=f"""Estimate realistic weekly active users in 1 year:

PRODUCT: {product_description[:300]}...

Your estimate:""",
        question_options=[
            "< 500 users",
            "500 - 1,000 users",
            "1,000 - 5,000 users",
            "5,000 - 10,000 users",
            "10,000 - 50,000 users",
            "50,000+ users"
        ]
    )

    user_survey = Survey([q_users])
    user_raw = runner.run(user_survey, agents_list, model, question_names=["user_estimate"])
    user_estimates = [
        r.get("user_estimate") for r in user_raw
        if r is not None and r.get("user_estimate") is not None
    ]

    cooldown = runner.get_cooldown()
    if cooldown > 0:
        if verbose:
            print(f"  Cooling down {cooldown:.0f}s...")
        time.sleep(cooldown)

    # Success likelihood
    q_success = QuestionLinearScale(
        question_name="success_likelihood",
        question_text="""Rate the overall likelihood of commercial success for this product (1 = Will fail, 10 = Will succeed):""",
        question_options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    )

    # Success likelihood
    success_survey = Survey([q_success])
    success_raw = runner.run(success_survey, agents_list, model, question_names=["success_likelihood"])
    success_scores = [
        r.get("success_likelihood") for r in success_raw
        if r is not None and r.get("success_likelihood") is not None
    ]
    
    return {
        "star_estimates": star_estimates,
        "user_estimates": user_estimates,
        "success_scores": success_scores,
        "avg_success": round(sum(success_scores) / len(success_scores), 2) if success_scores else 0,
    }


def analyze_go_to_market(market_data: Dict, success_data: Dict, verbose: bool = True) -> Dict:
    """Use LLM to generate go-to-market strategy."""
    
    prompt = f"""Analyze this market research data and create a go-to-market strategy.

## MARKET SURVEY RESULTS

**Willingness to Pay Scores (1-10):**
{market_data.get('would_pay', [])}

**Price Point Distribution:**
{market_data.get('price_points', [])}

**Segment Breakdown:**
{json.dumps(market_data.get('by_segment', {}), indent=2)}

## SUCCESS PREDICTIONS

**GitHub Star Estimates:**
{success_data.get('star_estimates', [])}

**User Estimates (1 year):**
{success_data.get('user_estimates', [])}

**Success Likelihood Avg:** {success_data.get('avg_success', 0)}/10

---

Create a go-to-market analysis in JSON:

```json
{{
  "target_segments": [
    {{
      "segment": "name",
      "description": "who they are",
      "why_they_buy": "motivation",
      "price_sensitivity": "low|medium|high",
      "recommended_price": "$X/month",
      "acquisition_channel": "how to reach them",
      "conversion_strategy": "how to convert them"
    }}
  ],
  "pricing_strategy": {{
    "model": "freemium|subscription|usage_based",
    "free_tier": "what's included",
    "pro_tier": {{"price": "$X", "features": [...]}},
    "team_tier": {{"price": "$X/user", "features": [...]}},
    "enterprise": "custom pricing approach"
  }},
  "growth_projections": {{
    "year_1_users": "X-Y range",
    "year_1_stars": "X-Y range",
    "year_1_revenue": "$X-Y range",
    "key_assumptions": ["assumption1", "assumption2"]
  }},
  "risks": ["risk1", "risk2"],
  "recommendations": ["action1", "action2", "action3"]
}}
```"""

    try:
        if verbose:
            print("  Generating go-to-market strategy with LLM...")
        
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', result.stdout, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
    except Exception as e:
        print(f"  GTM analysis error: {e}")
    
    return {}


def run_full_market_analysis(
    project_path: Optional[Union[str, Path]] = None,
    product_description: Optional[str] = None,
    use_cache: bool = True,
    verbose: bool = True,
) -> Dict:
    """Run complete market analysis."""
    
    config = get_config()
    cache_file = config.cache_dir / "market_analysis.json"
    
    # Check cache
    if use_cache and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
                if verbose:
                    print("Using cached market analysis")
                return cached
        except Exception:
            pass
    
    # Get product description
    if product_description is None:
        if project_path:
            product_description = read_project_readme(project_path)
    
    if not product_description:
        return {"error": "No product description provided"}
    
    if verbose:
        print("="*60)
        print("MARKET ANALYSIS")
        print("="*60)
    
    # Run market survey
    if verbose:
        print("\n[1/3] Running market survey...")
    market_data = run_market_survey(product_description, verbose=verbose)
    
    # Run success prediction
    if verbose:
        print("\n[2/3] Running success prediction...")
    success_data = run_success_prediction(product_description, verbose=verbose)
    
    # Generate GTM strategy
    if verbose:
        print("\n[3/3] Generating go-to-market strategy...")
    gtm = analyze_go_to_market(market_data, success_data, verbose=verbose)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "market_survey": market_data,
        "success_prediction": success_data,
        "go_to_market": gtm,
    }
    
    # Cache
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    if verbose:
        print_summary(result)
    
    return result


def print_summary(result: Dict):
    """Print summary of market analysis."""
    
    print("\n" + "="*60)
    print("MARKET ANALYSIS SUMMARY")
    print("="*60)
    
    market = result.get("market_survey", {})
    success = result.get("success_prediction", {})
    gtm = result.get("go_to_market", {})
    
    # Willingness to pay
    wtp = market.get("would_pay", [])
    if wtp:
        avg_wtp = sum(wtp) / len(wtp)
        pct_would_pay = len([w for w in wtp if w >= 6]) / len(wtp) * 100
        print(f"\n💰 WILLINGNESS TO PAY")
        print(f"   Average score: {avg_wtp:.1f}/10")
        print(f"   Would pay (>=6): {pct_would_pay:.0f}%")
    
    # Price points
    prices = market.get("price_points", [])
    if prices:
        print(f"\n💵 PRICE POINT DISTRIBUTION")
        from collections import Counter
        for price, count in Counter(prices).most_common():
            pct = count / len(prices) * 100
            print(f"   {price}: {pct:.0f}%")
    
    # Success prediction
    print(f"\n📈 SUCCESS PREDICTIONS")
    print(f"   Avg success likelihood: {success.get('avg_success', 0)}/10")
    
    # GTM highlights
    if gtm:
        print(f"\n🎯 GO-TO-MARKET HIGHLIGHTS")
        
        pricing = gtm.get("pricing_strategy", {})
        if pricing:
            print(f"   Pricing model: {pricing.get('model', 'TBD')}")
        
        projections = gtm.get("growth_projections", {})
        if projections:
            print(f"\n   Year 1 Projections:")
            print(f"   • Users: {projections.get('year_1_users', 'TBD')}")
            print(f"   • Stars: {projections.get('year_1_stars', 'TBD')}")
            print(f"   • Revenue: {projections.get('year_1_revenue', 'TBD')}")


def get_market_summary() -> str:
    """Get market analysis summary for prompts."""
    
    config = get_config()
    cache_file = config.cache_dir / "market_analysis.json"
    
    if not cache_file.exists():
        return "No market analysis available. Run market analysis first."
    
    with open(cache_file) as f:
        data = json.load(f)
    
    market = data.get("market_survey", {})
    success = data.get("success_prediction", {})
    gtm = data.get("go_to_market", {})
    
    wtp = market.get("would_pay", [])
    avg_wtp = sum(wtp) / len(wtp) if wtp else 0
    
    summary = f"""## Market Analysis Summary

**Willingness to Pay:** {avg_wtp:.1f}/10
**Success Likelihood:** {success.get('avg_success', 0)}/10

**Pricing Strategy:** {gtm.get('pricing_strategy', {}).get('model', 'TBD')}

**Target Segments:**
"""
    
    for seg in gtm.get("target_segments", [])[:3]:
        summary += f"- {seg.get('segment')}: {seg.get('recommended_price', 'TBD')}\n"
    
    proj = gtm.get("growth_projections", {})
    summary += f"""
**Year 1 Projections:**
- Users: {proj.get('year_1_users', 'TBD')}
- Stars: {proj.get('year_1_stars', 'TBD')}
- Revenue: {proj.get('year_1_revenue', 'TBD')}
"""
    
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Market analysis")
    parser.add_argument("path", nargs="?", help="Path to project or README")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    args = parser.parse_args()
    
    if args.summary:
        print(get_market_summary())
    else:
        run_full_market_analysis(
            project_path=args.path,
            use_cache=not args.no_cache,
        )
