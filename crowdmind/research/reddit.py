"""
Reddit Research Agent

Searches Reddit for user pain points in any topic area.
Extracts common complaints, feature requests, and workflow pain points.
"""

import json
import time
import requests
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import subprocess

from crowdmind.config import get_config


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CrowdMindResearch/1.0"
}


def fetch_subreddit_posts(subreddit: str, limit: int = 25) -> List[Dict]:
    """Fetch recent posts from a subreddit using JSON API."""
    posts = []
    
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for post in data.get('data', {}).get('children', []):
                p = post.get('data', {})
                posts.append({
                    "source": "reddit",
                    "title": p.get('title', ''),
                    "content": p.get('selftext', '')[:500],
                    "score": p.get('score', 0),
                    "comments": p.get('num_comments', 0),
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                    "subreddit": subreddit,
                    "created": datetime.fromtimestamp(p.get('created_utc', 0)).isoformat(),
                })
        
        time.sleep(1)  # Be nice to Reddit
        
    except Exception as e:
        print(f"  Error fetching r/{subreddit}: {e}")
    
    return posts


def search_reddit(query: str, limit: int = 15) -> List[Dict]:
    """Search Reddit for posts matching a query."""
    posts = []
    
    try:
        from urllib.parse import quote_plus
        url = f"https://www.reddit.com/search.json?q={quote_plus(query)}&limit={limit}&sort=relevance&t=month"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for post in data.get('data', {}).get('children', []):
                p = post.get('data', {})
                posts.append({
                    "source": "reddit",
                    "title": p.get('title', ''),
                    "content": p.get('selftext', '')[:500],
                    "score": p.get('score', 0),
                    "comments": p.get('num_comments', 0),
                    "url": f"https://reddit.com{p.get('permalink', '')}",
                    "subreddit": p.get('subreddit', ''),
                    "query": query,
                })
        
        time.sleep(1)
        
    except Exception as e:
        print(f"  Error searching '{query}': {e}")
    
    return posts


def filter_relevant_posts(posts: List[Dict], keywords: List[str] = None) -> List[Dict]:
    """Filter posts for relevance to pain points."""
    
    pain_keywords = [
        "frustrat", "annoying", "problem", "issue", "bug", "slow",
        "rate limit", "expensive", "losing", "lost", "context",
        "workflow", "switch", "multiple", "session", "terminal",
        "wish", "want", "need", "should", "please", "help",
        "hate", "terrible", "awful", "worst", "disappointed",
    ]
    
    if keywords:
        pain_keywords.extend(keywords)
    
    relevant = []
    for post in posts:
        text = (post.get('title', '') + ' ' + post.get('content', '')).lower()
        
        pain_score = sum(1 for kw in pain_keywords if kw in text)
        
        if pain_score >= 2:
            post['pain_score'] = pain_score
            relevant.append(post)
    
    relevant.sort(key=lambda x: (x.get('pain_score', 0), x.get('score', 0)), reverse=True)
    
    return relevant


def extract_pain_points_with_llm(posts: List[Dict]) -> Dict:
    """Use LLM to extract structured pain points from posts."""
    
    posts_text = ""
    for i, post in enumerate(posts[:20]):
        posts_text += f"\n---POST {i+1}---\n"
        posts_text += f"Title: {post.get('title', '')}\n"
        posts_text += f"Content: {post.get('content', '')[:300]}\n"
        posts_text += f"Subreddit: r/{post.get('subreddit', '')}\n"
        posts_text += f"Score: {post.get('score', 0)}, Comments: {post.get('comments', 0)}\n"
    
    prompt = f"""Analyze these Reddit posts and extract user pain points.

POSTS:
{posts_text}

Extract and categorize the pain points that a product could solve.

Output as JSON:
```json
{{
  "pain_points": [
    {{
      "category": "workflow|cost|reliability|performance|usability|other",
      "description": "Clear description of the pain point",
      "frequency": "high|medium|low",
      "example_quote": "Direct quote from a post",
      "potential_solution": "How a product could solve this"
    }}
  ],
  "feature_requests": [
    {{
      "request": "What users are asking for",
      "votes": "How many seem to want this (estimate)",
      "feasibility": "easy|medium|hard"
    }}
  ],
  "top_frustrations": ["frustration1", "frustration2", "..."],
  "opportunities": ["opportunity1", "opportunity2", "..."]
}}
```"""

    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            response = result.stdout
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
    except Exception as e:
        print(f"LLM analysis failed: {e}")
    
    return {}


def run_research(
    subreddits: List[str] = None,
    search_queries: List[str] = None,
    use_cache: bool = True,
    verbose: bool = True,
    cache_hours: int = 6,
) -> Dict:
    """Run Reddit research for pain points."""
    
    config = get_config()
    cache_file = config.cache_dir / "reddit_research.json"
    
    if subreddits is None:
        subreddits = config.reddit_subreddits
    
    if search_queries is None:
        search_queries = [
            "frustrated workflow",
            "annoying problem developer",
            "wish there was a tool",
        ]
    
    # Check cache
    if use_cache and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
                cache_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
                if datetime.now() - cache_time < timedelta(hours=cache_hours):
                    if verbose:
                        print("Using cached Reddit research")
                    return cached
        except Exception:
            pass
    
    if verbose:
        print("Researching Reddit for user pain points...")
    
    all_posts = []
    
    # Fetch from subreddits
    for sub in subreddits:
        if verbose:
            print(f"  Fetching r/{sub}...")
        posts = fetch_subreddit_posts(sub)
        relevant = filter_relevant_posts(posts)
        all_posts.extend(relevant)
        if verbose:
            print(f"    Found {len(relevant)} relevant posts")
    
    # Run search queries
    if verbose:
        print("  Running search queries...")
    for query in search_queries[:5]:
        posts = search_reddit(query)
        relevant = filter_relevant_posts(posts)
        all_posts.extend(relevant)
    
    # Deduplicate by URL
    seen = set()
    unique_posts = []
    for post in all_posts:
        if post.get('url') not in seen:
            seen.add(post.get('url'))
            unique_posts.append(post)
    
    if verbose:
        print(f"\n  Total unique relevant posts: {len(unique_posts)}")
    
    # Analyze with LLM
    if verbose:
        print("  Analyzing with LLM...")
    analysis = extract_pain_points_with_llm(unique_posts)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "posts_analyzed": len(unique_posts),
        "top_posts": unique_posts[:10],
        "analysis": analysis,
    }
    
    # Cache results
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    if verbose:
        print(f"\nReddit Research Complete!")
        if analysis.get('top_frustrations'):
            print("\nTop User Frustrations:")
            for f in analysis['top_frustrations'][:5]:
                print(f"  - {f}")
        if analysis.get('opportunities'):
            print("\nOpportunities:")
            for o in analysis['opportunities'][:5]:
                print(f"  - {o}")
    
    return result


def get_pain_points_summary() -> str:
    """Get a text summary of pain points for use in prompts."""
    
    config = get_config()
    cache_file = config.cache_dir / "reddit_research.json"
    
    if not cache_file.exists():
        return "No Reddit research available. Run research first."
    
    with open(cache_file) as f:
        research = json.load(f)
    
    analysis = research.get('analysis', {})
    
    pain_points = analysis.get('pain_points', [])
    frustrations = analysis.get('top_frustrations', [])
    opportunities = analysis.get('opportunities', [])
    
    summary = f"""## Reddit User Pain Points

**Top Frustrations:**
{chr(10).join(f'- {f}' for f in frustrations[:7])}

**Key Pain Points:**
"""
    
    for pp in pain_points[:5]:
        summary += f"\n**{pp.get('category', 'unknown').upper()}**: {pp.get('description', '')}"
        if pp.get('potential_solution'):
            summary += f"\n  → Solution: {pp.get('potential_solution')}"
    
    summary += f"""

**Opportunities:**
{chr(10).join(f'- {o}' for o in opportunities[:5])}

**Posts Analyzed:** {research.get('posts_analyzed', 0)}
"""
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Research Reddit for pain points")
    parser.add_argument("--subreddits", nargs="+", help="Subreddits to search")
    parser.add_argument("--queries", nargs="+", help="Search queries")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    parser.add_argument("--summary", action="store_true", help="Print summary")
    args = parser.parse_args()
    
    if args.summary:
        print(get_pain_points_summary())
    else:
        run_research(
            subreddits=args.subreddits,
            search_queries=args.queries,
            use_cache=not args.no_cache,
        )
