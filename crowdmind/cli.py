"""
CrowdMind CLI

A command-line interface for product research and validation.
"""

import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="crowdmind",
    help="AI-Powered Research & Validation for Products",
    no_args_is_help=True,
)

console = Console()


# Common options
def common_options(func):
    """Decorator for common CLI options."""
    func = typer.Option(None, "--personas", "-p", help="Number of personas to use")(func)
    return func


@app.command()
def analyze(
    path: Path = typer.Argument(..., help="Path to project or README file"),
    personas: int = typer.Option(10, "--personas", "-p", help="Number of personas"),
    pack: Optional[str] = typer.Option(None, "--pack", help="Persona pack (developers, enterprise, mixed)"),
    users: Optional[List[str]] = typer.Option(None, "--users", "-u", help="Custom user types"),
    provider: str = typer.Option("anthropic", "--provider", help="LLM provider"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """
    Run full analysis pipeline on a project.
    
    Includes: codebase analysis, research, ideation, and validation.
    """
    from crowdmind.research.codebase import run_analysis as analyze_codebase
    from crowdmind.research.multi import run_multi_research
    from crowdmind.ideate.features import run_ideation
    from crowdmind.validate.panel import run_evaluation
    from crowdmind.report.markdown import generate_report
    
    if not quiet:
        console.print(Panel.fit(
            "[bold blue]CrowdMind Analysis[/bold blue]\n"
            f"Project: {path}",
            border_style="blue"
        ))
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=quiet,
    ) as progress:
        # Step 1: Codebase analysis
        task = progress.add_task("Analyzing codebase...", total=None)
        results["codebase"] = analyze_codebase(path, verbose=verbose)
        progress.update(task, completed=True)
        
        # Step 2: Research
        task = progress.add_task("Researching market...", total=None)
        results["research"] = run_multi_research(use_cache=True, verbose=verbose)
        progress.update(task, completed=True)
        
        # Step 3: Ideation
        task = progress.add_task("Generating ideas...", total=None)
        results["ideation"] = run_ideation(num_ideas=5, verbose=verbose)
        progress.update(task, completed=True)
        
        # Step 4: Validation
        task = progress.add_task("Validating with personas...", total=None)
        readme_path = path / "README.md" if path.is_dir() else path
        if readme_path.exists():
            readme_content = readme_path.read_text()
            results["validation"] = run_evaluation(
                readme_content=readme_content,
                verbose=verbose,
                num_agents=personas,
            )
        progress.update(task, completed=True)
    
    # Generate report
    report = generate_report(results)
    
    if output:
        output.write_text(report)
        if not quiet:
            console.print(f"\n[green]Report saved to:[/green] {output}")
    else:
        console.print(report)
    
    # Summary
    if not quiet and results.get("validation"):
        val = results["validation"]
        console.print(Panel(
            f"[bold]Star Rate:[/bold] {val.get('star_rate', 0)}%\n"
            f"[bold]Avg Score:[/bold] {val.get('avg_star', 0)}/10\n"
            f"[bold]Personas:[/bold] {val.get('agents_evaluated', 0)}",
            title="Validation Summary",
            border_style="green" if val.get('star_rate', 0) >= 50 else "yellow"
        ))


@app.command()
def validate(
    idea: str = typer.Argument(..., help="Idea or README content to validate"),
    personas: int = typer.Option(10, "--personas", "-p", help="Number of personas"),
    pack: Optional[str] = typer.Option(None, "--pack", help="Persona pack"),
    categories: Optional[List[str]] = typer.Option(None, "--categories", "-c", help="Persona categories"),
    context: Optional[Path] = typer.Option(None, "--context", help="Path to product/codebase for context"),
    product: Optional[str] = typer.Option(None, "--product", help="Product description for context"),
    provider: str = typer.Option("anthropic", "--provider", help="LLM provider"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (JSON)"),
    simple: bool = typer.Option(False, "--simple", help="Use simple single-score mode (default is multi-metric)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """
    Validate a single idea with AI personas.
    
    Metrics: Interest, Usefulness, Urgency, Would Pay (+ qualitative feedback)
    
    Pass a product description, README content, or path to README file.
    Use --context to analyze your codebase for better context-aware evaluation.
    """
    import json
    
    # Check if idea is a file path
    idea_path = Path(idea)
    if idea_path.exists():
        content = idea_path.read_text()
    else:
        content = idea
    
    # Build product context
    context_prompt = ""
    if context or product:
        from crowdmind.context import build_context
        ctx = build_context(path=context, description=product, analyze_code=True, verbose=verbose)
        context_prompt = ctx.to_prompt()
        if not quiet:
            console.print(f"[dim]Context: {ctx.name}[/dim]")
            if ctx.tech_stack:
                console.print(f"[dim]Tech: {', '.join(ctx.tech_stack[:5])}[/dim]")
            if ctx.existing_features:
                console.print(f"[dim]Features detected: {len(ctx.existing_features)} (from codebase analysis)[/dim]")
    
    # Default is multi-metric (Interest, Usefulness, Urgency, Would Pay)
    # Use --simple for old single-score mode
    use_multi = not simple
    
    if not quiet:
        console.print(Panel.fit(
            "[bold blue]CrowdMind Validation[/bold blue]\n"
            f"Personas: {personas}",
            border_style="blue"
        ))
    
    if use_multi:
        # Use new multi-metric survey
        from crowdmind.validate.survey import run_multi_metric_survey
        import time
        
        if not quiet:
            console.print(f"\n[dim]Creating {personas} AI personas...[/dim]")
            console.print(f"[dim]Asking each: interest, usefulness, urgency, would pay[/dim]")
            console.print(f"[dim]Adaptive rate limiting: auto-adjusting concurrency[/dim]")
            console.print(f"[dim]Estimated time: ~{personas * 3}s[/dim]\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Surveying {personas} personas...", total=None)
                result = run_multi_metric_survey(
                    content=content,
                    context_prompt=context_prompt,
                    num_agents=personas,
                    verbose=False,
                    report_api_issues=True,
                )
                progress.update(task, description="[green]✓ Done![/green]")
                time.sleep(0.5)  # Let user see the "Done" message
        else:
            result = run_multi_metric_survey(
                content=content,
                context_prompt=context_prompt,
                num_agents=personas,
                verbose=False,
                report_api_issues=not quiet,
            )
        
        if output:
            output.write_text(json.dumps({
                "scores": result.scores,
                "would_pay": result.would_pay,
                "synthesis": result.synthesis,
                "recommendations": result.recommendations,
                "feedback": [{"persona": f.persona_name, "scores": f.scores, "reasoning": f.reasoning} for f in result.feedback]
            }, indent=2))
            if not quiet:
                console.print(f"\n[green]Results saved to:[/green] {output}")
        
        # Display results
        if not quiet:
            table = Table(title="Multi-Metric Validation Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Score", style="green")
            table.add_column("Rating", style="yellow")
            
            for metric, score in result.scores.items():
                rating = "🟢 High" if score >= 7 else "🟡 Medium" if score >= 5 else "🔴 Low"
                table.add_row(metric.title(), f"{score}/10", rating)
            
            console.print(table)
            
            # Would pay breakdown
            console.print("\n[bold]Would Pay:[/bold]")
            console.print(f"  Yes: {int(result.would_pay.get('yes', 0)*100)}%")
            console.print(f"  Maybe: {int(result.would_pay.get('maybe', 0)*100)}%")
            console.print(f"  No: {int(result.would_pay.get('no', 0)*100)}%")
            
            # Synthesis
            console.print(f"\n[bold]Synthesis:[/bold]\n{result.synthesis}")
            
            # Top feedback
            if result.feedback and verbose:
                console.print("\n[bold]Persona Feedback:[/bold]")
                for fb in result.feedback[:5]:
                    console.print(f"\n[cyan]{fb.persona_name}[/cyan] ({fb.persona_category})")
                    console.print(f"  Scores: {fb.scores}")
                    if fb.reasoning:
                        console.print(f"  [dim]{fb.reasoning[:200]}...[/dim]" if len(fb.reasoning) > 200 else f"  [dim]{fb.reasoning}[/dim]")
            
            # Recommendations
            if result.recommendations:
                console.print("\n[bold]Recommendations:[/bold]")
                for rec in result.recommendations:
                    console.print(f"  • {rec}")
    else:
        # Use original single-metric evaluation
        from crowdmind.validate.panel import run_evaluation
        result = run_evaluation(
            readme_content=content,
            verbose=verbose and not quiet,
            num_agents=personas,
            categories=categories,
        )
        
        if output:
            output.write_text(json.dumps(result, indent=2))
            if not quiet:
                console.print(f"\n[green]Results saved to:[/green] {output}")
        
        # Display results
        if not quiet:
            table = Table(title="Validation Results (Simple Mode)")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Recommend Rate", f"{result.get('star_rate', 0)}%")
            table.add_row("Avg Appeal Score", f"{result.get('avg_star', 0)}/10")
            table.add_row("Overall Score", f"{result.get('total_score', 0)}/100")
            table.add_row("Personas Evaluated", str(result.get("agents_evaluated", 0)))
            
            console.print(table)
            
            # Category breakdown
            if result.get("by_category"):
                console.print("\n[bold]By Category:[/bold]")
                for cat, data in sorted(result["by_category"].items(), key=lambda x: x[1]["avg"], reverse=True):
                    console.print(f"  {cat}: {data['avg']}/10")


@app.command()
def optimize(
    path: Path = typer.Argument(..., help="Path to content to optimize (README, pitch, etc.)"),
    target: float = typer.Option(80.0, "--target", "-t", help="Target score (0-100)"),
    iterations: int = typer.Option(10, "--iterations", "-i", help="Maximum iterations"),
    metric: str = typer.Option("overall", "--metric", "-m", help="Metric to optimize (overall, interest, usefulness, urgency)"),
    context: Optional[Path] = typer.Option(None, "--context", help="Path to product for context"),
    product: Optional[str] = typer.Option(None, "--product", help="Product description for context"),
    personas: int = typer.Option(
        5,
        "--personas",
        "-p",
        help="Personas per evaluation (lower = fewer parallel API calls, less 429)",
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save final content to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """
    Autoresearch loop: iteratively optimize content until target score.
    
    Uses Karpathy-style experimentation: propose → test → keep/discard → repeat.
    """
    from crowdmind.optimize import run_optimization
    
    # Read content
    content = path.read_text()
    
    # Build context
    context_prompt = ""
    if context or product:
        from crowdmind.context import build_context
        ctx = build_context(path=context, description=product)
        context_prompt = ctx.to_prompt()
    
    if not quiet:
        console.print(Panel.fit(
            "[bold blue]CrowdMind Autoresearch Optimization[/bold blue]\n"
            f"Target: {target}/100 | Max iterations: {iterations}\n"
            f"Metric: {metric}\n"
            f"[dim]Adaptive rate limiting enabled[/dim]",
            border_style="blue"
        ))
    
    result = run_optimization(
        content=content,
        context_prompt=context_prompt,
        target=target,
        max_iterations=iterations,
        metric=metric,
        verbose=not quiet,
        num_agents=personas,
    )

    if not quiet:
        # Summary
        console.print("\n" + "="*60)
        console.print("[bold]OPTIMIZATION COMPLETE[/bold]")
        console.print("="*60)
        console.print(f"Initial score: {result.initial_score:.1f}/100")
        console.print(f"Final score: {result.final_score:.1f}/100")
        console.print(f"Improvement: {result.final_score - result.initial_score:+.1f}")
        console.print(f"Iterations: {result.iterations}")
        console.print(f"Target reached: {'✓ Yes' if result.target_reached else '✗ No'}")
        
        if result.improvements_made:
            console.print("\n[bold]Improvements made:[/bold]")
            for i, imp in enumerate(result.improvements_made, 1):
                console.print(f"  {i}. {imp}")
    
    if output:
        output.write_text(result.final_content)
        if not quiet:
            console.print(f"\n[green]Optimized content saved to:[/green] {output}")


@app.command()
def research(
    path: Optional[Path] = typer.Argument(None, help="Path to project (optional)"),
    sources: List[str] = typer.Option(
        ["reddit", "hackernews", "github"], 
        "--sources", "-s", 
        help="Sources to research"
    ),
    topics: Optional[List[str]] = typer.Option(None, "--topics", "-t", help="Custom topics to search"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """
    Research market pain points from multiple sources.
    
    Sources: reddit, hackernews, github
    """
    from crowdmind.research.multi import run_multi_research, get_multi_research_summary
    import json
    
    if not quiet:
        console.print(Panel.fit(
            "[bold blue]CrowdMind Research[/bold blue]\n"
            f"Sources: {', '.join(sources)}",
            border_style="blue"
        ))
        console.print()
        console.print("[dim]Searching for pain points and frustrations...[/dim]")
        for source in sources:
            if source == "reddit":
                console.print("[dim]  → Querying Reddit API...[/dim]")
            elif source == "hackernews":
                console.print("[dim]  → Querying Hacker News (Algolia)...[/dim]")
            elif source == "github":
                console.print("[dim]  → Searching GitHub Issues...[/dim]")
        console.print()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing discussions...", total=None)
            result = run_multi_research(
                use_cache=not no_cache,
                verbose=False,
                sources=sources,
            )
            progress.update(task, description="[green]✓ Research complete![/green]")
            import time
            time.sleep(0.5)
    else:
        result = run_multi_research(
            use_cache=not no_cache,
            verbose=verbose,
            sources=sources,
        )
    
    if output:
        output.write_text(json.dumps(result, indent=2))
        if not quiet:
            console.print(f"\n[green]Results saved to:[/green] {output}")
    
    # Display summary
    if not quiet:
        summary = get_multi_research_summary()
        console.print(summary)


@app.command()
def market(
    path: Path = typer.Argument(..., help="Path to project or README"),
    personas: int = typer.Option(10, "--personas", "-p", help="Number of buyer personas"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
):
    """
    Run market analysis on a project.
    
    Includes: buyer personas, pricing analysis, success predictions.
    """
    from crowdmind.market.analysis import run_full_market_analysis, get_market_summary
    import json
    
    if not quiet:
        console.print(Panel.fit(
            "[bold blue]CrowdMind Market Analysis[/bold blue]\n"
            f"Project: {path}",
            border_style="blue"
        ))
        console.print()
        console.print("[dim]Running market analysis...[/dim]")
        console.print("[dim]  → Generating buyer personas...[/dim]")
        console.print("[dim]  → Analyzing pricing strategies...[/dim]")
        console.print("[dim]  → Predicting market success...[/dim]")
        console.print()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing market...", total=None)
            result = run_full_market_analysis(
                project_path=path,
                use_cache=not no_cache,
                verbose=False,
            )
            progress.update(task, description="[green]✓ Analysis complete![/green]")
            import time
            time.sleep(0.5)
    else:
        result = run_full_market_analysis(
            project_path=path,
            use_cache=not no_cache,
            verbose=verbose,
        )
    
    if output:
        output.write_text(json.dumps(result, indent=2))
        if not quiet:
            console.print(f"\n[green]Results saved to:[/green] {output}")
    
    if not quiet:
        summary = get_market_summary()
        console.print(summary)


@app.command()
def personas():
    """
    Interactive wizard to create custom personas.
    
    [Stub - Coming soon]
    """
    from crowdmind.validate.personas import PERSONA_PACKS, Persona
    
    console.print(Panel.fit(
        "[bold blue]CrowdMind Personas[/bold blue]\n"
        "Interactive persona creation wizard",
        border_style="blue"
    ))
    
    console.print("\n[bold]Available Persona Packs:[/bold]")
    for name, pack in PERSONA_PACKS.items():
        console.print(f"  [cyan]{name}[/cyan]: {pack.description} ({len(pack.personas)} personas)")
    
    console.print("\n[yellow]Interactive wizard coming soon![/yellow]")
    console.print("For now, use --pack option with validate/analyze commands.")


@app.command()
def demo():
    """
    Show a demo of CrowdMind capabilities.
    
    [Stub - Coming soon]
    """
    console.print(Panel.fit(
        "[bold blue]CrowdMind Demo[/bold blue]\n"
        "Interactive demonstration",
        border_style="blue"
    ))
    
    console.print("\n[yellow]Demo mode coming soon![/yellow]")
    console.print("\nTry these commands instead:")
    console.print("  [cyan]crowdmind validate \"My SaaS idea description\"[/cyan]")
    console.print("  [cyan]crowdmind research --sources reddit hackernews[/cyan]")
    console.print("  [cyan]crowdmind analyze ./my-project[/cyan]")


@app.command()
def config():
    """
    Setup wizard for CrowdMind configuration.
    
    [Stub - Coming soon]
    """
    from crowdmind.config import CONFIG_FILE, get_config
    
    console.print(Panel.fit(
        "[bold blue]CrowdMind Configuration[/bold blue]",
        border_style="blue"
    ))
    
    cfg = get_config()
    
    console.print(f"\n[bold]Config file:[/bold] {CONFIG_FILE}")
    console.print(f"[bold]Config exists:[/bold] {CONFIG_FILE.exists()}")
    
    console.print("\n[bold]Current Settings:[/bold]")
    console.print(f"  Default model: {cfg.default_model}")
    console.print(f"  Default personas: {cfg.default_personas}")
    console.print(f"  Default provider: {cfg.default_provider}")
    console.print(f"  Cache dir: {cfg.cache_dir}")
    
    console.print("\n[bold]API Keys:[/bold]")
    console.print(f"  OpenAI: {'[green]configured[/green]' if cfg.openai_api_key else '[red]not set[/red]'}")
    console.print(f"  Anthropic: {'[green]configured[/green]' if cfg.anthropic_api_key else '[red]not set[/red]'}")
    console.print(f"  Google: {'[green]configured[/green]' if cfg.google_api_key else '[red]not set[/red]'}")
    console.print(f"  Groq: {'[green]configured[/green]' if cfg.groq_api_key else '[red]not set[/red]'}")
    console.print(f"  GitHub: {'[green]configured[/green]' if cfg.github_token else '[red]not set[/red]'}")
    
    console.print("\n[yellow]Interactive setup wizard coming soon![/yellow]")
    console.print("\nFor now, set environment variables:")
    console.print("  export ANTHROPIC_API_KEY=your-key")
    console.print("  export CROWDMIND_MODEL=claude-sonnet-4-6")
    console.print("  export CROWDMIND_PERSONAS=15")


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
):
    """
    CrowdMind - AI-Powered Research & Validation for Products
    """
    if version:
        from crowdmind import __version__
        console.print(f"crowdmind version {__version__}")
        raise typer.Exit()
    
    # If no command provided, show help
    if ctx.invoked_subcommand is None and not version:
        console.print(ctx.get_help())
        raise typer.Exit()


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
