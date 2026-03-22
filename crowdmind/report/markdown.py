"""
Report Generation

Generates markdown reports from analysis results.
"""

from datetime import datetime
from typing import Dict, Optional
from pathlib import Path


def generate_report(results: Dict, title: str = "CrowdMind Analysis Report") -> str:
    """
    Generate a comprehensive markdown report from analysis results.
    
    Args:
        results: Dictionary containing analysis results from various modules
        title: Report title
    
    Returns:
        Markdown formatted report string
    """
    
    report = f"""# {title}

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

"""
    
    # Codebase Analysis
    if results.get("codebase"):
        codebase = results["codebase"]
        report += """## 📂 Codebase Analysis

"""
        
        tech = codebase.get("tech_stack", {})
        if tech:
            report += f"""### Tech Stack
- **Languages:** {', '.join(tech.get('languages', [])) or 'Not detected'}
- **Frameworks:** {', '.join(tech.get('frameworks', [])) or 'Not detected'}
- **Build Tools:** {', '.join(tech.get('build_tools', [])) or 'Not detected'}

"""
        
        files = codebase.get("source_files", {})
        if files:
            total = sum(files.values())
            report += f"""### Source Files
Total: {total} files

"""
            for lang, count in files.items():
                if count > 0:
                    report += f"- {lang}: {count}\n"
            report += "\n"
        
        llm = codebase.get("llm_analysis", {})
        if llm.get("features"):
            report += """### Detected Features
"""
            for f in llm["features"][:10]:
                report += f"- {f}\n"
            report += "\n"
        
        if llm.get("extension_points"):
            report += """### Extension Points
"""
            for e in llm["extension_points"][:5]:
                report += f"- {e}\n"
            report += "\n"
    
    # Research Results
    if results.get("research"):
        research = results["research"]
        report += """## 🔍 Market Research

"""
        
        stats = research.get("source_stats", {})
        if stats:
            report += """### Sources Analyzed
"""
            for source, s in stats.items():
                report += f"- **{source}:** {s.get('relevant', 0)} relevant posts (from {s.get('total', 0)} total)\n"
            report += "\n"
        
        analysis = research.get("analysis", {})
        
        if analysis.get("top_frustrations"):
            report += """### Top User Frustrations
"""
            for i, f in enumerate(analysis["top_frustrations"][:5], 1):
                report += f"{i}. {f}\n"
            report += "\n"
        
        if analysis.get("opportunities"):
            report += """### Opportunities
"""
            for o in analysis["opportunities"][:5]:
                report += f"- {o}\n"
            report += "\n"
        
        if analysis.get("pain_points"):
            report += """### Key Pain Points
"""
            for pp in analysis["pain_points"][:5]:
                category = pp.get('category', 'unknown').upper()
                description = pp.get('description', '')
                sources = ', '.join(pp.get('sources', []))
                report += f"- **[{category}]** {description}\n"
                if sources:
                    report += f"  - Sources: {sources}\n"
                if pp.get('potential_solution'):
                    report += f"  - Potential solution: {pp['potential_solution']}\n"
            report += "\n"
    
    # Feature Ideas
    if results.get("ideation"):
        ideation = results["ideation"]
        ideas = ideation.get("ideas", [])
        
        if ideas:
            report += """## 💡 Feature Ideas

"""
            # Sort by star potential
            ideas_sorted = sorted(
                ideas, 
                key=lambda x: x.get('star_potential', {}).get('score', 0),
                reverse=True
            )
            
            for idea in ideas_sorted[:5]:
                star = idea.get('star_potential', {}).get('score', 0)
                effort = idea.get('implementation', {}).get('estimated_effort', 'unknown')
                
                report += f"""### {idea.get('name', 'Unnamed')} ⭐ {star}/10

> {idea.get('tagline', '')}

**Problem:** {idea.get('problem', '')}

**Solution:** {idea.get('solution', '')}

**Effort:** {effort} | **Complexity:** {idea.get('implementation', {}).get('complexity', 'unknown')}

---

"""
    
    # Validation Results
    if results.get("validation"):
        val = results["validation"]
        report += """## ✅ Validation Results

"""
        
        report += f"""### Overall Scores
- **Star Rate (>=7/10):** {val.get('star_rate', 0)}%
- **Average Score:** {val.get('avg_star', 0)}/10
- **Total Score:** {val.get('total_score', 0)}/100
- **Personas Evaluated:** {val.get('agents_evaluated', 0)}

"""
        
        by_cat = val.get("by_category", {})
        if by_cat:
            report += """### By Persona Category
"""
            for cat, data in sorted(by_cat.items(), key=lambda x: x[1]['avg'], reverse=True):
                report += f"- **{cat}:** {data['avg']}/10 (n={len(data['scores'])})\n"
            report += "\n"
        
        scores = val.get("scores", [])
        if scores:
            report += f"""### Score Distribution
- Min: {min(scores)}
- Max: {max(scores)}
- Median: {sorted(scores)[len(scores)//2]}

"""
    
    # Market Analysis
    if results.get("market"):
        market_result = results["market"]
        report += """## 📊 Market Analysis

"""
        
        market = market_result.get("market_survey", {})
        wtp = market.get("would_pay", [])
        if wtp:
            avg_wtp = sum(wtp) / len(wtp)
            pct_pay = len([w for w in wtp if w >= 6]) / len(wtp) * 100
            report += f"""### Willingness to Pay
- **Average Score:** {avg_wtp:.1f}/10
- **Would Pay (>=6):** {pct_pay:.0f}%

"""
        
        success = market_result.get("success_prediction", {})
        if success:
            report += f"""### Success Predictions
- **Success Likelihood:** {success.get('avg_success', 0)}/10

"""
        
        gtm = market_result.get("go_to_market", {})
        if gtm:
            pricing = gtm.get("pricing_strategy", {})
            if pricing:
                report += f"""### Pricing Strategy
- **Model:** {pricing.get('model', 'TBD')}
- **Free Tier:** {pricing.get('free_tier', 'TBD')}

"""
            
            proj = gtm.get("growth_projections", {})
            if proj:
                report += f"""### Year 1 Projections
- **Users:** {proj.get('year_1_users', 'TBD')}
- **Stars:** {proj.get('year_1_stars', 'TBD')}
- **Revenue:** {proj.get('year_1_revenue', 'TBD')}

"""
    
    # Footer
    report += """---

*Report generated by CrowdMind*
"""
    
    return report


def generate_summary(results: Dict) -> str:
    """
    Generate a brief summary from analysis results.
    
    Args:
        results: Dictionary containing analysis results
    
    Returns:
        Brief summary string
    """
    
    summary_parts = []
    
    if results.get("validation"):
        val = results["validation"]
        summary_parts.append(
            f"Validation: {val.get('star_rate', 0)}% star rate, "
            f"{val.get('avg_star', 0)}/10 avg score"
        )
    
    if results.get("research"):
        research = results["research"]
        total = research.get("total_posts", 0)
        summary_parts.append(f"Research: {total} relevant posts analyzed")
    
    if results.get("ideation"):
        ideas = results["ideation"].get("ideas", [])
        if ideas:
            top_idea = max(ideas, key=lambda x: x.get('star_potential', {}).get('score', 0))
            summary_parts.append(
                f"Top idea: {top_idea.get('name')} "
                f"({top_idea.get('star_potential', {}).get('score', 0)}/10 star potential)"
            )
    
    if results.get("market"):
        market = results["market"]
        success = market.get("success_prediction", {})
        summary_parts.append(f"Success likelihood: {success.get('avg_success', 0)}/10")
    
    return " | ".join(summary_parts) if summary_parts else "No analysis results available"


def save_report(
    results: Dict,
    output_path: Path,
    title: str = "CrowdMind Analysis Report"
) -> str:
    """
    Generate and save a markdown report.
    
    Args:
        results: Analysis results
        output_path: Path to save the report
        title: Report title
    
    Returns:
        Path to saved report
    """
    
    report = generate_report(results, title)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    
    return str(output_path)


if __name__ == "__main__":
    # Demo with sample data
    sample_results = {
        "validation": {
            "star_rate": 65.0,
            "avg_star": 7.2,
            "total_score": 72.0,
            "agents_evaluated": 10,
            "scores": [6, 7, 8, 7, 8, 6, 7, 8, 9, 6],
            "by_category": {
                "power_user": {"avg": 8.0, "scores": [8, 8]},
                "skeptic": {"avg": 6.0, "scores": [6, 6]},
            }
        },
        "research": {
            "total_posts": 45,
            "source_stats": {
                "reddit": {"total": 30, "relevant": 25},
                "hackernews": {"total": 20, "relevant": 15},
            },
            "analysis": {
                "top_frustrations": [
                    "Rate limits are frustrating",
                    "Context loss between sessions",
                    "High costs for API usage",
                ],
                "opportunities": [
                    "Cost tracking and optimization",
                    "Session persistence",
                ],
            }
        }
    }
    
    print(generate_report(sample_results))
