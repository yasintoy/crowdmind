"""
GitHub Issues Research Agent

Fetches and analyzes issues from GitHub repositories
to find user pain points and feature requests.
"""

import os
import time
import requests
from typing import List, Dict, Optional

from crowdmind.config import get_api_key


HEADERS = {
    "User-Agent": "Mozilla/5.0 CrowdMindResearch/1.0",
    "Accept": "application/vnd.github.v3+json"
}


def fetch_github_issues(
    repo: str,
    limit: int = 30,
    state: str = "all",
    labels: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Fetch recent issues from a GitHub repo.
    
    Args:
        repo: Repository in format "owner/repo"
        limit: Maximum issues to fetch
        state: Issue state ("open", "closed", "all")
        labels: Filter by labels
    """
    issues = []
    
    try:
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {
            "state": state,
            "per_page": limit,
            "sort": "created",
            "direction": "desc",
        }
        
        if labels:
            params["labels"] = ",".join(labels)
        
        headers = {**HEADERS}
        
        # Add token if available for higher rate limits
        token = get_api_key("github")
        if token:
            headers["Authorization"] = f"token {token}"
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for issue in data:
                # Skip pull requests
                if 'pull_request' in issue:
                    continue
                
                issues.append({
                    "source": "github",
                    "title": issue.get('title', ''),
                    "content": (issue.get('body', '') or '')[:500],
                    "score": issue.get('reactions', {}).get('total_count', 0),
                    "comments": issue.get('comments', 0),
                    "url": issue.get('html_url', ''),
                    "repo": repo,
                    "state": issue.get('state', ''),
                    "labels": [l.get('name') for l in issue.get('labels', [])],
                    "created": issue.get('created_at', ''),
                    "issue_number": issue.get('number'),
                })
        
        time.sleep(1)  # Rate limit respect
        
    except Exception as e:
        print(f"  GitHub {repo} error: {e}")
    
    return issues


def search_github_issues(
    query: str,
    limit: int = 30,
    language: Optional[str] = None,
) -> List[Dict]:
    """
    Search GitHub issues across repositories.
    
    Args:
        query: Search query
        limit: Maximum results
        language: Filter by programming language
    """
    issues = []
    
    try:
        from urllib.parse import quote_plus
        
        q = f"{query} type:issue"
        if language:
            q += f" language:{language}"
        
        url = f"https://api.github.com/search/issues"
        params = {
            "q": q,
            "per_page": limit,
            "sort": "reactions",
            "order": "desc",
        }
        
        headers = {**HEADERS}
        token = get_api_key("github")
        if token:
            headers["Authorization"] = f"token {token}"
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for issue in data.get('items', []):
                issues.append({
                    "source": "github_search",
                    "title": issue.get('title', ''),
                    "content": (issue.get('body', '') or '')[:500],
                    "score": issue.get('reactions', {}).get('total_count', 0),
                    "comments": issue.get('comments', 0),
                    "url": issue.get('html_url', ''),
                    "repo": issue.get('repository_url', '').split('repos/')[-1],
                    "state": issue.get('state', ''),
                    "labels": [l.get('name') for l in issue.get('labels', [])],
                    "created": issue.get('created_at', ''),
                })
        
        time.sleep(1)
        
    except Exception as e:
        print(f"  GitHub search error: {e}")
    
    return issues


def fetch_repo_issues_batch(
    repos: List[str],
    limit_per_repo: int = 30,
    verbose: bool = True,
) -> Dict:
    """
    Fetch issues from multiple repos.
    
    Args:
        repos: List of repos in "owner/repo" format
        limit_per_repo: Issues per repo
        verbose: Print progress
    """
    all_issues = []
    repo_stats = {}
    
    for repo in repos:
        if verbose:
            print(f"  Fetching {repo}...")
        
        issues = fetch_github_issues(repo, limit=limit_per_repo)
        all_issues.extend(issues)
        repo_stats[repo] = len(issues)
    
    return {
        "issues": all_issues,
        "repo_stats": repo_stats,
        "total": len(all_issues),
    }


def filter_pain_point_issues(issues: List[Dict]) -> List[Dict]:
    """Filter issues that indicate pain points."""
    
    pain_keywords = [
        "bug", "error", "crash", "broken", "not working", "doesn't work",
        "feature request", "enhancement", "please add", "would be nice",
        "slow", "performance", "timeout", "rate limit",
        "confusing", "unclear", "documentation", "help",
        "breaking change", "regression", "unexpected",
    ]
    
    pain_labels = [
        "bug", "enhancement", "feature request", "help wanted",
        "good first issue", "question", "documentation",
    ]
    
    relevant = []
    for issue in issues:
        text = (issue.get('title', '') + ' ' + issue.get('content', '')).lower()
        labels = [l.lower() for l in issue.get('labels', [])]
        
        # Score based on keywords
        pain_score = sum(1 for kw in pain_keywords if kw in text)
        
        # Bonus for pain-related labels
        label_score = sum(1 for l in labels if any(pl in l for pl in pain_labels))
        
        total_score = pain_score + label_score
        
        if total_score >= 2:
            issue['pain_score'] = total_score
            relevant.append(issue)
    
    relevant.sort(key=lambda x: (x.get('pain_score', 0), x.get('score', 0)), reverse=True)
    
    return relevant


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch GitHub issues")
    parser.add_argument("repo", help="Repository (owner/repo)")
    parser.add_argument("--limit", type=int, default=20, help="Number of issues")
    parser.add_argument("--state", choices=["open", "closed", "all"], default="all")
    parser.add_argument("--search", help="Search query instead of repo issues")
    args = parser.parse_args()
    
    if args.search:
        issues = search_github_issues(args.search, limit=args.limit)
        print(f"\nSearch results for '{args.search}':")
    else:
        issues = fetch_github_issues(args.repo, limit=args.limit, state=args.state)
        print(f"\nIssues from {args.repo}:")
    
    for issue in issues[:10]:
        state_icon = "🟢" if issue['state'] == 'open' else "🔴"
        print(f"  {state_icon} [{issue['score']} reactions] {issue['title'][:60]}...")
        if issue.get('labels'):
            print(f"     Labels: {', '.join(issue['labels'][:3])}")
