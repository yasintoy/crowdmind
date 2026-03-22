"""
Multi-Source Research Agent

Orchestrates research across multiple platforms:
- Reddit
- Hacker News
- GitHub Issues

Aggregates and deduplicates pain points across all sources.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from crowdmind.config import get_config
from crowdmind.research.reddit import fetch_subreddit_posts, search_reddit
from crowdmind.research.hackernews import search_hackernews, fetch_hn_comments
from crowdmind.research.github import fetch_github_issues


def filter_pain_points(posts: List[Dict]) -> List[Dict]:
    """Filter posts that indicate pain points."""
    
    pain_keywords = [
        "frustrat", "annoying", "problem", "issue", "bug", "slow", "broken",
        "rate limit", "expensive", "cost", "losing", "lost", "context",
        "workflow", "switch", "multiple", "session", "terminal", "crash",
        "wish", "want", "need", "should", "please", "help", "stuck",
        "hate", "terrible", "awful", "worst", "disappointed", "useless",
        "doesn't work", "not working", "can't", "cannot", "impossible",
    ]
    
    relevant = []
    for post in posts:
        text = (post.get('title', '') + ' ' + post.get('content', '')).lower()
        
        pain_score = sum(1 for kw in pain_keywords if kw in text)
        
        if pain_score >= 2:
            post['pain_score'] = pain_score
            relevant.append(post)
    
    relevant.sort(key=lambda x: (x.get('pain_score', 0), x.get('score', 0)), reverse=True)
    
    return relevant


def deduplicate_posts(posts: List[Dict]) -> List[Dict]:
    """Remove duplicate posts by URL."""
    seen = set()
    unique = []
    
    for post in posts:
        url = post.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(post)
    
    return unique


def analyze_with_llm(posts: List[Dict], verbose: bool = True) -> Dict:
    """Use LLM to extract structured pain points."""
    
    # Group by source
    by_source = {}
    for post in posts[:50]:
        source = post.get('source', 'unknown')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(post)
    
    # Build summary
    posts_text = ""
    for source, source_posts in by_source.items():
        posts_text += f"\n\n=== {source.upper()} ({len(source_posts)} posts) ===\n"
        for p in source_posts[:10]:
            posts_text += f"\n- [{p.get('score', 0)} pts] {p.get('title', '')[:100]}\n"
            if p.get('content'):
                posts_text += f"  {p.get('content', '')[:200]}...\n"
    
    prompt = f"""Analyze these posts from multiple platforms.

POSTS FROM REDDIT, HACKER NEWS, GITHUB:
{posts_text}

Extract pain points that a product could solve.

Output as JSON:
```json
{{
  "pain_points": [
    {{
      "category": "workflow|cost|reliability|performance|usability|other",
      "description": "Clear description",
      "frequency": "high|medium|low",
      "sources": ["reddit", "hackernews"],
      "example_quote": "Direct quote",
      "potential_solution": "How to solve this"
    }}
  ],
  "feature_requests": [
    {{
      "request": "What users want",
      "sources": ["source1"],
      "demand_level": "high|medium|low"
    }}
  ],
  "top_frustrations": ["1", "2", "3", "4", "5"],
  "opportunities": ["opp1", "opp2", "opp3"],
  "source_breakdown": {{
    "reddit": {{"posts": N, "key_themes": ["theme1"]}},
    "hackernews": {{"posts": N, "key_themes": ["theme1"]}},
    "github": {{"posts": N, "key_themes": ["theme1"]}}
  }}
}}
```"""

    try:
        if verbose:
            print("  Analyzing with LLM...")
        
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
        print(f"  LLM analysis error: {e}")
    
    return {}


def run_multi_research(
    use_cache: bool = True,
    verbose: bool = True,
    sources: List[str] = None,
    subreddits: List[str] = None,
    search_topics: List[str] = None,
    github_repos: List[str] = None,
    hn_searches: List[str] = None,
) -> Dict:
    """
    Run research across all configured sources.
    
    Args:
        use_cache: Use cached results if available
        verbose: Print progress
        sources: Sources to search ["reddit", "hackernews", "github"]
        subreddits: Custom subreddits to search
        search_topics: Custom search topics
        github_repos: Custom GitHub repos to check
        hn_searches: Custom HN search queries
    """
    
    config = get_config()
    cache_file = config.cache_dir / "multi_research.json"
    
    if sources is None:
        sources = ["reddit", "hackernews", "github"]
    
    if subreddits is None:
        subreddits = config.reddit_subreddits
    
    if search_topics is None:
        search_topics = [
            "frustrated developer workflow",
            "annoying tool problem",
            "wish there was a better way",
            "slow performance issue",
        ]
    
    if github_repos is None:
        github_repos = []  # User should provide relevant repos
    
    if hn_searches is None:
        hn_searches = [
            "developer tools",
            "productivity software",
            "workflow automation",
        ]
    
    # Check cache
    if use_cache and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
                cache_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
                if datetime.now() - cache_time < timedelta(hours=config.cache_hours):
                    if verbose:
                        print("Using cached multi-source research")
                    return cached
        except Exception:
            pass
    
    if verbose:
        print("="*60)
        print("MULTI-SOURCE RESEARCH")
        print("="*60)
    
    all_posts = []
    source_stats = {}
    
    # Reddit
    if "reddit" in sources:
        if verbose:
            print("\n[1/3] Searching Reddit...")
        
        reddit_posts = []
        for sub in subreddits:
            if verbose:
                print(f"  r/{sub}...")
            reddit_posts.extend(fetch_subreddit_posts(sub))
        
        for query in search_topics[:5]:
            reddit_posts.extend(search_reddit(query))
        
        reddit_posts = deduplicate_posts(reddit_posts)
        reddit_relevant = filter_pain_points(reddit_posts)
        all_posts.extend(reddit_relevant)
        source_stats['reddit'] = {'total': len(reddit_posts), 'relevant': len(reddit_relevant)}
        
        if verbose:
            print(f"  Found {len(reddit_relevant)} relevant posts")
    
    # Hacker News
    if "hackernews" in sources:
        if verbose:
            print("\n[2/3] Searching Hacker News...")
        
        hn_posts = []
        for query in hn_searches:
            if verbose:
                print(f"  Searching: {query}...")
            stories = search_hackernews(query)
            hn_posts.extend(stories)
            
            # Get comments from top stories
            for story in stories[:3]:
                story_id = story.get('story_id')
                if story_id:
                    comments = fetch_hn_comments(story_id, limit=20)
                    hn_posts.extend(comments)
        
        hn_posts = deduplicate_posts(hn_posts)
        hn_relevant = filter_pain_points(hn_posts)
        all_posts.extend(hn_relevant)
        source_stats['hackernews'] = {'total': len(hn_posts), 'relevant': len(hn_relevant)}
        
        if verbose:
            print(f"  Found {len(hn_relevant)} relevant posts/comments")
    
    # GitHub Issues
    if "github" in sources and github_repos:
        if verbose:
            print("\n[3/3] Fetching GitHub Issues...")
        
        github_issues = []
        for repo in github_repos:
            if verbose:
                print(f"  {repo}...")
            issues = fetch_github_issues(repo)
            github_issues.extend(issues)
        
        github_issues = deduplicate_posts(github_issues)
        github_relevant = filter_pain_points(github_issues)
        all_posts.extend(github_relevant)
        source_stats['github'] = {'total': len(github_issues), 'relevant': len(github_relevant)}
        
        if verbose:
            print(f"  Found {len(github_relevant)} relevant issues")
    
    # Deduplicate across sources
    all_posts = deduplicate_posts(all_posts)
    
    if verbose:
        print(f"\n  Total unique relevant posts: {len(all_posts)}")
    
    # Analyze with LLM
    analysis = analyze_with_llm(all_posts, verbose=verbose)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "sources": sources,
        "source_stats": source_stats,
        "total_posts": len(all_posts),
        "top_posts": all_posts[:20],
        "analysis": analysis,
    }
    
    # Cache
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    if verbose:
        print("\n" + "="*60)
        print("RESEARCH COMPLETE")
        print("="*60)
        
        print("\nSource Breakdown:")
        for source, stats in source_stats.items():
            print(f"  {source}: {stats['relevant']} relevant / {stats['total']} total")
        
        if analysis.get('top_frustrations'):
            print("\nTop Frustrations:")
            for f in analysis['top_frustrations'][:5]:
                print(f"  - {f}")
        
        if analysis.get('opportunities'):
            print("\nOpportunities:")
            for o in analysis['opportunities'][:5]:
                print(f"  - {o}")
    
    return result


def get_multi_research_summary() -> str:
    """Get summary for use in prompts."""
    
    config = get_config()
    cache_file = config.cache_dir / "multi_research.json"
    
    if not cache_file.exists():
        return "No multi-source research available. Run research first."
    
    with open(cache_file) as f:
        data = json.load(f)
    
    analysis = data.get('analysis', {})
    stats = data.get('source_stats', {})
    
    summary = """## Multi-Source Research Summary

**Sources Analyzed:**
"""
    
    for source, s in stats.items():
        summary += f"- {source}: {s.get('relevant', 0)} relevant posts\n"
    
    summary += f"\n**Total Posts Analyzed:** {data.get('total_posts', 0)}\n"
    
    if analysis.get('top_frustrations'):
        summary += "\n**Top Frustrations:**\n"
        for f in analysis['top_frustrations'][:5]:
            summary += f"- {f}\n"
    
    if analysis.get('pain_points'):
        summary += "\n**Key Pain Points:**\n"
        for pp in analysis['pain_points'][:5]:
            sources = ', '.join(pp.get('sources', []))
            summary += f"- [{pp.get('category')}] {pp.get('description')} (from: {sources})\n"
    
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-source research")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    parser.add_argument("--sources", nargs="+", default=["reddit", "hackernews"],
                       help="Sources to search (reddit, hackernews, github)")
    parser.add_argument("--subreddits", nargs="+", help="Subreddits to search")
    parser.add_argument("--github-repos", nargs="+", help="GitHub repos to check")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    args = parser.parse_args()
    
    if args.summary:
        print(get_multi_research_summary())
    else:
        run_multi_research(
            use_cache=not args.no_cache,
            sources=args.sources,
            subreddits=args.subreddits,
            github_repos=args.github_repos,
        )
