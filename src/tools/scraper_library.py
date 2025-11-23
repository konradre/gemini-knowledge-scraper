"""
Production Scraper Library - Challenge-Compliant Content Extractors

All scrapers in this library are:
1. Challenge-compliant (NOT banned services)
2. Designed for content extraction (RAG/LLM ready)
3. Don't require complex pageFunction configuration
4. Return clean text/markdown/html suitable for Gemini

Categories:
- Official Apify scrapers (highest quality, FREE)
- Community content crawlers (specialized features)
- AI-focused scrapers (optimized for RAG/LLM)
"""

from typing import List, Dict

# ========== OFFICIAL APIFY SCRAPERS (FREE, HIGH QUALITY) ==========

OFFICIAL_SCRAPERS = [
    {
        'id': 'apify/website-content-crawler',
        'name': 'Website Content Crawler',
        'stats': {'runs': {'total': 87679, 'finished': 82679, 'failed': 5000}},
        'pricingModel': 'FREE',
        'title': 'Website Content Crawler - LLM content extraction',
        'username': 'apify',
        'success_rate': 0.948,
        'monthly_users': 4650,
        'rating': 4.36,
        'best_for': ['documentation', 'blog', 'general'],
        'output_format': 'markdown',  # Primary format
        'features': ['markdown', 'text', 'html', 'file_download', 'anti_blocking'],
        'speed': 'medium',
        'cost': 'free'
    },
    {
        'id': 'apify/rag-web-browser',
        'name': 'RAG Web Browser',
        'stats': {'runs': {'total': 7503, 'finished': 7445, 'failed': 58}},
        'pricingModel': 'FREE',
        'title': 'RAG Web Browser - OpenAI Assistant compatible',
        'username': 'apify',
        'success_rate': 0.992,
        'monthly_users': 682,
        'rating': 4.93,
        'best_for': ['documentation', 'blog', 'news'],
        'output_format': 'markdown',
        'features': ['markdown', 'google_search', 'fast', 'anti_blocking'],
        'speed': 'fast',
        'cost': 'free'
    },
    {
        'id': 'apify/cheerio-scraper',
        'name': 'Cheerio Scraper',
        'stats': {'runs': {'total': 10860, 'finished': 10780, 'failed': 80}},
        'pricingModel': 'FREE',
        'title': 'Cheerio Scraper - Fast HTML parsing',
        'username': 'apify',
        'success_rate': 0.993,
        'monthly_users': 607,
        'rating': 4.93,
        'best_for': ['general', 'simple_sites'],
        'output_format': 'html',
        'features': ['fast', 'no_javascript'],
        'speed': 'very_fast',
        'cost': 'free'
    },
    {
        'id': 'apify/beautifulsoup-scraper',
        'name': 'BeautifulSoup Scraper',
        'stats': {'runs': {'total': 928, 'finished': 910, 'failed': 18}},
        'pricingModel': 'FREE',
        'title': 'BeautifulSoup Scraper - Python alternative',
        'username': 'apify',
        'success_rate': 0.981,
        'monthly_users': 12,
        'rating': 4.24,
        'best_for': ['general', 'simple_sites'],
        'output_format': 'html',
        'features': ['python', 'fast'],
        'speed': 'fast',
        'cost': 'free'
    }
]

# ========== COMMUNITY AI-FOCUSED SCRAPERS ==========

COMMUNITY_AI_SCRAPERS = [
    {
        'id': 'janbuchar/crawl4ai',
        'name': 'Crawl4AI',
        'stats': {'runs': {'total': 658, 'finished': 590, 'failed': 68}},
        'pricingModel': 'FREE',
        'title': 'Crawl4AI - Open-source AI content retrieval',
        'username': 'janbuchar',
        'success_rate': 0.897,
        'monthly_users': 22,
        'rating': 3.26,
        'best_for': ['documentation', 'blog'],
        'output_format': 'text',
        'features': ['ai_optimized'],
        'speed': 'medium',
        'cost': 'free'
    },
    {
        'id': 'quaking_pail/ai-website-content-markdown-scraper',
        'name': 'AI Website Content Markdown Scraper',
        'stats': {'runs': {'total': 817, 'finished': 761, 'failed': 56}},
        'pricingModel': 'PER_RESULT',
        'title': 'AI Markdown Scraper - LLM optimized',
        'username': 'quaking_pail',
        'success_rate': 0.932,
        'monthly_users': 22,
        'rating': 3.93,
        'best_for': ['documentation', 'blog'],
        'output_format': 'markdown',
        'features': ['markdown', 'ai_optimized'],
        'speed': 'medium',
        'cost': 'paid'  # $30 per 1000
    }
]

# ========== COMBINED PRODUCTION LIBRARY ==========

def get_scraper_library() -> List[Dict]:
    """
    Get full production scraper library (Challenge-compliant only).

    Returns list of scraper metadata for intelligent selection.
    """
    return OFFICIAL_SCRAPERS + COMMUNITY_AI_SCRAPERS


def get_scrapers_by_budget(budget_mode: str) -> List[Dict]:
    """
    Filter scrapers by budget preference.

    Args:
        budget_mode: 'minimal', 'optimal', or 'premium'

    Returns:
        Filtered list of scrapers matching budget
    """
    all_scrapers = get_scraper_library()

    if budget_mode == 'minimal':
        # Only FREE scrapers, prioritize speed
        return [s for s in all_scrapers if s['cost'] == 'free' and s['speed'] in ['very_fast', 'fast']]

    elif budget_mode == 'optimal':
        # FREE scrapers with good balance of speed and features
        return [s for s in all_scrapers if s['cost'] == 'free']

    else:  # premium
        # All scrapers, prioritize quality and features
        return all_scrapers


def get_scrapers_by_target_type(target_type: str) -> List[Dict]:
    """
    Filter scrapers by target type.

    Args:
        target_type: 'documentation', 'blog', 'forum', 'news', 'general'

    Returns:
        Scrapers best suited for target type
    """
    all_scrapers = get_scraper_library()
    return [s for s in all_scrapers if target_type in s['best_for']]


def score_scraper_production(scraper: Dict, budget_mode: str, target_type: str) -> float:
    """
    Production scoring algorithm for scraper selection.

    Factors:
    - Success rate (40%)
    - User popularity (20%)
    - Cost efficiency (20%)
    - Target type match (10%)
    - Output format (10%)

    Args:
        scraper: Scraper metadata dict
        budget_mode: User's budget preference
        target_type: Target website type

    Returns:
        Score from 0-100 (higher = better)
    """
    score = 0.0

    # Success rate (0-40 points)
    score += scraper['success_rate'] * 40

    # Popularity (0-20 points) - log scale
    import math
    monthly_users = scraper['monthly_users']
    if monthly_users > 0:
        # Normalize: 1 user = 5 points, 1000 users = 15 points, 5000+ users = 20 points
        popularity_score = min(20, 5 + (math.log10(monthly_users) * 5))
        score += popularity_score

    # Cost efficiency (0-20 points)
    if scraper['cost'] == 'free':
        score += 20
    elif budget_mode == 'premium':
        score += 10  # Willing to pay for premium scrapers

    # Target type match (0-10 points)
    if target_type in scraper['best_for']:
        score += 10

    # Output format bonus (0-10 points)
    if scraper['output_format'] == 'markdown':
        score += 10  # Best for Gemini
    elif scraper['output_format'] == 'text':
        score += 7
    elif scraper['output_format'] == 'html':
        score += 5

    return round(score, 1)
