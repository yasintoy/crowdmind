"""
CrowdMind Research Module

Research user pain points from multiple sources.
"""

from crowdmind.research.codebase import run_analysis as analyze_codebase
from crowdmind.research.reddit import run_research as research_reddit
from crowdmind.research.hackernews import search_hackernews, fetch_hn_comments
from crowdmind.research.github import fetch_github_issues
from crowdmind.research.multi import run_multi_research

__all__ = [
    "analyze_codebase",
    "research_reddit",
    "search_hackernews",
    "fetch_hn_comments",
    "fetch_github_issues",
    "run_multi_research",
]
