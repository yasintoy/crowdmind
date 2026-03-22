"""
Hacker News Research Agent

Searches Hacker News for discussions and pain points.
Uses the Algolia HN API (free, no auth required).
"""

import time
import requests
from typing import List, Dict
from urllib.parse import quote_plus


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CrowdMindResearch/1.0"
}


def search_hackernews(query: str, limit: int = 20) -> List[Dict]:
    """Search Hacker News via Algolia API."""
    posts = []
    
    try:
        url = f"https://hn.algolia.com/api/v1/search?query={quote_plus(query)}&tags=story&hitsPerPage={limit}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for hit in data.get('hits', []):
                posts.append({
                    "source": "hackernews",
                    "title": hit.get('title', ''),
                    "content": "",  # HN stories don't have body text
                    "score": hit.get('points', 0),
                    "comments": hit.get('num_comments', 0),
                    "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "author": hit.get('author', ''),
                    "created": hit.get('created_at', ''),
                    "story_id": hit.get('objectID', ''),
                })
        
        time.sleep(0.5)
        
    except Exception as e:
        print(f"  HN search error: {e}")
    
    return posts


def fetch_hn_comments(story_id: str, limit: int = 50) -> List[Dict]:
    """Fetch comments from a HN story."""
    comments = []
    
    try:
        url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage={limit}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for hit in data.get('hits', []):
                comment_text = hit.get('comment_text', '')
                if comment_text:
                    comments.append({
                        "source": "hackernews_comment",
                        "title": f"Comment on story {story_id}",
                        "content": comment_text[:500],
                        "score": hit.get('points', 0) or 0,
                        "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                        "author": hit.get('author', ''),
                        "created": hit.get('created_at', ''),
                        "story_id": story_id,
                    })
        
        time.sleep(0.5)
        
    except Exception as e:
        print(f"  HN comments error: {e}")
    
    return comments


def search_hn_with_comments(
    queries: List[str],
    stories_per_query: int = 10,
    comments_per_story: int = 20,
    verbose: bool = True,
) -> Dict:
    """Search HN and fetch comments from top stories."""
    
    all_posts = []
    all_comments = []
    
    for query in queries:
        if verbose:
            print(f"  Searching HN: {query}...")
        
        stories = search_hackernews(query, limit=stories_per_query)
        all_posts.extend(stories)
        
        # Get comments from top stories
        for story in stories[:3]:
            story_id = story.get('story_id')
            if story_id:
                comments = fetch_hn_comments(story_id, limit=comments_per_story)
                all_comments.extend(comments)
    
    return {
        "stories": all_posts,
        "comments": all_comments,
        "total_stories": len(all_posts),
        "total_comments": len(all_comments),
    }


def filter_pain_point_content(posts: List[Dict]) -> List[Dict]:
    """Filter HN posts/comments for pain point indicators."""
    
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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Search Hacker News")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--comments", action="store_true", help="Also fetch comments")
    parser.add_argument("--limit", type=int, default=10, help="Number of stories")
    args = parser.parse_args()
    
    stories = search_hackernews(args.query, limit=args.limit)
    
    print(f"\nFound {len(stories)} stories:")
    for story in stories[:10]:
        print(f"  [{story['score']} pts] {story['title'][:60]}...")
    
    if args.comments and stories:
        story_id = stories[0].get('story_id')
        if story_id:
            comments = fetch_hn_comments(story_id, limit=20)
            print(f"\nTop story comments ({len(comments)}):")
            for c in comments[:5]:
                print(f"  - {c['content'][:100]}...")
