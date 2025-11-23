"""
Scraper Selection Module for Gemini Knowledge Scraper

CRITICAL: Apify $1M Challenge compliance
- MUST filter all banned scrapers per challenge terms
- 100% accuracy required (zero violations)
- Test coverage: 100% pass rate mandatory

Banned categories (Section 2.3):
- Social media (Instagram, Facebook, TikTok, LinkedIn, Twitter, YouTube)
- E-commerce (Amazon)
- Search engines (Google Maps, Google Search, Google Trends)
- B2B platforms (Apollo)
"""

from typing import List, Dict, Optional, Tuple
from apify_client import ApifyClient
import re
from .scraper_library import (
    get_scraper_library,
    get_scrapers_by_budget,
    get_scrapers_by_target_type,
    score_scraper_production
)


# ========== BANNED PATTERNS (Challenge Compliance) ==========

BANNED_PATTERNS = [
    # Social Media
    'instagram',
    'facebook',
    'tiktok',
    'linkedin',
    'twitter',
    'x-scraper',
    'youtube',

    # E-Commerce
    'amazon',
    'amz-',

    # Search Engines
    'google-maps',
    'google-search',
    'google-trends',

    # B2B Platforms
    'apollo',
    'apollo-io'
]

# Whitelist of known good scrapers (MVP - for integration testing)
# Using website-content-crawler which is simple and doesn't require pageFunction
KNOWN_SCRAPERS = [
    {
        'id': 'apify/website-content-crawler',
        'name': 'Website Content Crawler',
        'stats': {'runs': {'total': 100000, 'finished': 95000, 'failed': 5000}},
        'pricingModel': 'PER_ACTOR_RUN',
        'title': 'Website Content Crawler - Extract full content',
        'username': 'apify'
    }
]


def is_scraper_banned(actor: Dict) -> bool:
    """
    Check if an Apify actor is banned per challenge terms.

    CRITICAL: This is the compliance gatekeeper. Must be 100% accurate.

    Args:
        actor: Actor dict with 'id', 'title', 'description' fields

    Returns:
        True if banned, False if allowed

    Examples:
        >>> is_scraper_banned({'id': 'apify/instagram-scraper'})
        True
        >>> is_scraper_banned({'id': 'apify/web-scraper'})
        False
    """
    # Combine all searchable text (case-insensitive)
    actor_id = actor.get('id', '').lower()
    title = actor.get('title', '').lower()
    description = actor.get('description', '').lower()

    searchable_text = f"{actor_id} {title} {description}"

    # Check against all banned patterns
    for pattern in BANNED_PATTERNS:
        if pattern in searchable_text:
            return True

    return False


def filter_banned_scrapers(actors: List[Dict]) -> List[Dict]:
    """
    Filter out all banned scrapers from a list.

    Args:
        actors: List of actor dictionaries

    Returns:
        List of allowed actors only

    Side effects:
        Logs each banned actor detected (for audit trail)
    """
    allowed = []
    banned_count = 0

    for actor in actors:
        if is_scraper_banned(actor):
            banned_count += 1
            # Log for audit (helps debug if false positives)
            actor_id = actor.get('id', 'unknown')
            print(f"🚫 Banned: {actor_id}")
        else:
            allowed.append(actor)

    print(f"✅ Filtered {banned_count} banned scrapers, {len(allowed)} allowed")
    return allowed


# ========== SCRAPER SCORING ==========

def score_scraper(actor: Dict, budget_mode: str = 'optimal') -> float:
    """
    Score a scraper based on quality metrics and budget mode.

    Scoring factors:
    - runs_count (popularity, reliability indicator)
    - rating (if available)
    - monthly_users (adoption indicator)
    - Budget mode preference (cost vs quality trade-off)

    Args:
        actor: Actor dictionary
        budget_mode: 'minimal', 'optimal', or 'premium'

    Returns:
        Score from 0-100 (higher = better)
    """
    score = 0.0

    # Base popularity score (runs_count)
    runs = actor.get('stats', {}).get('totalRuns', 0)
    if runs > 0:
        score += min(runs / 1000, 50)  # Max 50 points

    # Rating score (if available)
    rating = actor.get('rating', 0)
    if rating > 0:
        score += rating * 10  # Max 50 points (5-star rating)

    # Monthly users score
    monthly_users = actor.get('stats', {}).get('monthlyUsers', 0)
    if monthly_users > 0:
        score += min(monthly_users / 10, 20)  # Max 20 points

    # Budget mode adjustment
    # (In real implementation, would factor in pricing)
    if budget_mode == 'premium':
        # Prefer high-quality scrapers (boost rating weight)
        score *= 1.2
    elif budget_mode == 'minimal':
        # Prefer free/cheap scrapers (would check pricing here)
        score *= 0.9

    return min(score, 100.0)


def select_best_scrapers(
    actors: List[Dict],
    budget_mode: str = 'optimal',
    top_n: int = 3,
    target_type: str = 'general'
) -> List[Dict]:
    """
    Select the best N scrapers from a list, ordered by score.

    Args:
        actors: List of actor dictionaries (already banned-filtered)
        budget_mode: 'minimal', 'optimal', or 'premium'
        top_n: Number of top scrapers to return
        target_type: Type of target website

    Returns:
        List of top N scrapers, sorted by score (descending)
    """
    # Score all actors using production algorithm
    scored = []
    for actor in actors:
        score = score_scraper_production(actor, budget_mode, target_type)
        scored.append({
            'actor': actor,
            'score': score
        })

    # Sort by score (descending)
    scored.sort(key=lambda x: x['score'], reverse=True)

    # Return top N actors
    return [item['actor'] for item in scored[:top_n]]


# ========== TARGET CLASSIFICATION ==========

def classify_target(url: str) -> str:
    """
    Classify target URL to help select appropriate scraper type.

    Args:
        url: Target URL or domain

    Returns:
        Target type: 'documentation', 'blog', 'forum', 'ecommerce', 'news', 'general'
    """
    url_lower = url.lower()

    # Documentation patterns
    if any(pattern in url_lower for pattern in ['docs.', '/docs/', 'documentation', 'api.', 'developer.']):
        return 'documentation'

    # Blog patterns
    if any(pattern in url_lower for pattern in ['/blog/', 'blog.', 'medium.com', 'substack.com']):
        return 'blog'

    # Forum patterns
    if any(pattern in url_lower for pattern in ['forum', 'reddit.com', 'stackoverflow.com', 'discourse']):
        return 'forum'

    # News patterns
    if any(pattern in url_lower for pattern in ['news', 'article', 'press', '/story/']):
        return 'news'

    # Default to general web scraping
    return 'general'


async def find_and_select_scrapers(
    apify_client: ApifyClient,
    target: str,
    budget_mode: str = 'optimal',
    top_n: int = 3
) -> Tuple[List[Dict], str]:
    """
    Main function: Find suitable scrapers for a target and select the best ones.

    Workflow:
    1. Classify target type
    2. Search Apify Store for relevant scrapers
    3. Filter out banned scrapers (CRITICAL)
    4. Score and rank scrapers
    5. Return top N with fallbacks

    Args:
        apify_client: Initialized Apify client
        target: Target URL or domain
        budget_mode: 'minimal', 'optimal', or 'premium'
        top_n: Number of scrapers to return

    Returns:
        Tuple of (selected_scrapers, target_type)

    Raises:
        ValueError: If no allowed scrapers found after filtering
    """
    # Classify target
    target_type = classify_target(target)

    # Get production scraper library (Challenge-compliant only)
    actors = get_scraper_library()

    print(f"🔍 Production library: {len(actors)} Challenge-compliant scrapers")
    print(f"   Target type: {target_type}")
    print(f"   Budget mode: {budget_mode}")

    # CRITICAL: Filter banned scrapers
    allowed_actors = filter_banned_scrapers(actors)

    if not allowed_actors:
        raise ValueError(f"❌ No allowed scrapers found for target type '{target_type}'. All {len(actors)} scrapers were banned.")

    # Select best scrapers using production scoring
    selected = select_best_scrapers(allowed_actors, budget_mode, top_n, target_type)

    print(f"✅ Selected {len(selected)} scrapers:")
    for i, actor in enumerate(selected, 1):
        actor_id = actor.get('id', 'unknown')
        score = score_scraper_production(actor, budget_mode, target_type)
        print(f"   {i}. {actor_id} (score: {score:.1f})")

    return selected, target_type
