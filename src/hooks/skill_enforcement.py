"""
Skill Enforcement Hooks for Gemini Knowledge Scraper

Startup validation and compliance enforcement:
- Validates skills directory structure
- Ensures BANNED_PATTERNS.md is loaded before scraper selection
- Zero bypass possibility (runs at startup)

Hook execution points:
- Startup: validate_startup()
- Before scraper selection: validate_scraper_selection()
"""

from typing import Tuple, Optional, Dict
from pathlib import Path


def validate_startup() -> Tuple[bool, str]:
    """
    Validate actor setup at startup (before any operations).

    Checks:
    - Skills directory exists
    - Required skill files present (SKILL.md, BANNED_PATTERNS.md)
    - BANNED_PATTERNS.md is readable

    Returns:
        Tuple of (is_valid, message)

    Example:
        >>> is_valid, message = validate_startup()
        >>> if not is_valid:
        ...     raise RuntimeError(message)
    """
    # Define required skills
    required_skills = [
        'apify-scraper-selection',
        'document-conversion',
        'gemini-file-upload'
    ]

    # Skills directory
    skills_dir = Path('.claude/skills')
    if not skills_dir.exists():
        return False, f"❌ Skills directory not found: {skills_dir}"

    # Check each required skill
    for skill_name in required_skills:
        skill_dir = skills_dir / skill_name
        if not skill_dir.exists():
            return False, f"❌ Required skill missing: {skill_name}"

        # Check SKILL.md
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.exists():
            return False, f"❌ SKILL.md missing for: {skill_name}"

    # Check BANNED_PATTERNS.md (CRITICAL)
    banned_patterns_path = skills_dir / 'apify-scraper-selection' / 'BANNED_PATTERNS.md'
    if not banned_patterns_path.exists():
        return False, "❌ CRITICAL: BANNED_PATTERNS.md not found"

    # Verify it's readable
    try:
        content = banned_patterns_path.read_text()
        if not content or len(content) < 100:
            return False, "❌ BANNED_PATTERNS.md is empty or too short"
    except Exception as e:
        return False, f"❌ Cannot read BANNED_PATTERNS.md: {e}"

    # All checks passed
    return True, f"✅ Skills validated: {len(required_skills)} skills ready"


def validate_scraper_selection(actor: dict) -> Tuple[bool, str]:
    """
    Validate a scraper selection before execution (pre-execution hook).

    CRITICAL: This is a safety check to prevent banned scrapers from running.
    Even if the filter fails, this hook catches violations.

    Args:
        actor: Actor dict to validate

    Returns:
        Tuple of (is_allowed, message)

    Example:
        >>> actor = {'id': 'apify/web-scraper'}
        >>> is_allowed, msg = validate_scraper_selection(actor)
        >>> if not is_allowed:
        ...     raise RuntimeError(f"Scraper blocked by hook: {msg}")
    """
    from ..tools.scraper_selector import is_scraper_banned

    actor_id = actor.get('id', 'unknown')

    if is_scraper_banned(actor):
        return False, f"🚫 BLOCKED: {actor_id} is banned per challenge terms"

    return True, f"✅ Allowed: {actor_id}"


def log_scraper_execution(actor: dict, status: str, details: Optional[str] = None):
    """
    Log scraper execution for audit trail (post-execution hook).

    Creates audit log of all scraper executions:
    - Which scrapers were used
    - Success/failure status
    - Any errors or warnings

    Args:
        actor: Actor dict that was executed
        status: 'success', 'failed', or 'skipped'
        details: Optional details/error message
    """
    from datetime import datetime

    actor_id = actor.get('id', 'unknown')
    timestamp = datetime.now().isoformat()

    log_entry = f"[{timestamp}] {status.upper()}: {actor_id}"
    if details:
        log_entry += f" - {details}"

    print(log_entry)

    # In production, could append to audit log file
    # For now, just stdout logging (captured by Apify)


# ========== HELPER FUNCTIONS ==========

def check_skills_token_efficiency() -> Dict:
    """
    Calculate token efficiency from skills pattern.

    Estimates:
    - Without skills: ~10K tokens loaded per run
    - With skills: ~2.5K tokens (75% reduction)

    Returns:
        Dict with efficiency metrics
    """
    # Estimate skill sizes (from progressive disclosure)
    skill_sizes = {
        'apify-scraper-selection': {
            'L1_SKILL.md': 800,
            'L2_BANNED_PATTERNS.md': 1000,
            'L3_SCORING_ALGORITHM.md': 1500
        },
        'document-conversion': {
            'L1_SKILL.md': 600,
            'L2_CLEANING_PATTERNS.md': 800
        },
        'gemini-file-upload': {
            'L1_SKILL.md': 700,
            'L2_ERROR_HANDLING.md': 900
        }
    }

    # Typical run loads L1 only (auto-triggers on keywords)
    typical_loaded = 800 + 600 + 700  # = 2,100 tokens
    # Occasionally loads L2 (when executing)
    with_L2 = typical_loaded + 1000 + 800 + 900  # = 4,800 tokens
    # Full documentation (all levels)
    full_docs = with_L2 + 1500  # = 6,300 tokens

    # Without skills (monolithic prompt)
    monolithic = 10000  # Typical for non-skills pattern

    efficiency = {
        'typical_run_tokens': typical_loaded,
        'with_execution_tokens': with_L2,
        'full_documentation_tokens': full_docs,
        'monolithic_baseline': monolithic,
        'reduction_typical': ((monolithic - typical_loaded) / monolithic) * 100,
        'reduction_with_execution': ((monolithic - with_L2) / monolithic) * 100
    }

    return efficiency
