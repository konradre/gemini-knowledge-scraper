"""
Gemini Knowledge Scraper - Main Entry Point

Complete workflow:
1. Validate startup (skills, hooks)
2. Select optimal scraper (banned filter applied)
3. Execute scraping with fallback
4. Convert HTML → text documents
5. Upload to Gemini File Search Store
6. Generate query guide
7. Return corpus metadata + pricing

BORG patterns:
- Skills-first progressive disclosure (75% token reduction)
- Hook-based enforcement (zero bypass)
- Banned filter (100% compliance)
"""

from apify import Actor
from apify_client import ApifyClient
from pathlib import Path
from datetime import datetime
from typing import List
import asyncio

# Import our tools
from .tools.scraper_selector import (
    find_and_select_scrapers,
    is_scraper_banned
)
from .tools.document_converter import (
    convert_dataset_to_documents,
    calculate_indexing_cost
)
from .tools.gemini_uploader import (
    upload_to_gemini,
    generate_query_guide
)
from .hooks import skill_enforcement


async def execute_scraper_with_fallback(
    apify_client: ApifyClient,
    selected_scrapers: List[dict],
    target: str,
    max_pages: int
) -> dict:
    """
    Execute scraper with automatic fallback on failure.

    Args:
        apify_client: Apify client instance
        selected_scrapers: List of scrapers (primary + fallbacks)
        target: Target URL
        max_pages: Maximum pages to scrape

    Returns:
        Dict with success, data, scraper_used, errors
    """
    last_error = None

    for i, scraper in enumerate(selected_scrapers):
        scraper_id = scraper['id']

        try:
            Actor.log.info(f"Attempting scraper {i+1}/{len(selected_scrapers)}: {scraper_id}")

            # Validate with hook (safety check)
            is_allowed, message = skill_enforcement.validate_scraper_selection(scraper)
            if not is_allowed:
                Actor.log.warning(f"🚫 Hook blocked: {message}")
                continue

            # Run scraper (HTML/web pages only)
            run = apify_client.actor(scraper_id).call(
                run_input={
                    'startUrls': [{'url': target}],
                    'maxCrawlPages': max_pages,
                    'maxConcurrency': 5,
                    'saveMarkdown': True  # Get markdown for better formatting
                }
            )

            # Get dataset
            dataset_items = apify_client.dataset(run['defaultDatasetId']).list_items()
            items = list(dataset_items.items)

            if items:
                Actor.log.info(f"✅ Scraper succeeded: {scraper_id} ({len(items)} items)")

                # Log execution for audit
                skill_enforcement.log_scraper_execution(scraper, 'success', f"{len(items)} items")

                return {
                    'success': True,
                    'data': items,
                    'scraper_used': scraper_id,
                    'errors': []
                }
            else:
                last_error = f"No data returned from {scraper_id}"
                Actor.log.warning(f"⚠️  {last_error}")

        except Exception as e:
            last_error = str(e)
            Actor.log.warning(f"⚠️  Scraper {scraper_id} failed: {last_error}")
            skill_enforcement.log_scraper_execution(scraper, 'failed', last_error)
            continue

    # All scrapers failed
    return {
        'success': False,
        'data': [],
        'scraper_used': None,
        'errors': [last_error] if last_error else ['All scrapers failed']
    }


async def main():
    async with Actor:
        # ========== STARTUP ==========

        Actor.log.info("🚀 Gemini Knowledge Scraper starting...")

        input_data = await Actor.get_input()

        # Validate required inputs
        required = ['target', 'gemini_api_key', 'apify_token']
        for field in required:
            if field not in input_data:
                raise ValueError(f"Missing required input: {field}")

        # Setup workspace
        workspace = Path("/tmp/scraper-workspace")
        workspace.mkdir(parents=True, exist_ok=True)
        docs_dir = workspace / "documents"
        docs_dir.mkdir(exist_ok=True)

        # Validate skills (hook enforcement)
        Actor.log.info("Validating skills directory...")
        is_valid, message = skill_enforcement.validate_startup()
        if not is_valid:
            raise RuntimeError(f"❌ Skills validation failed: {message}")
        Actor.log.info(message)

        # ========== PHASE 1: SCRAPER SELECTION ==========

        Actor.log.info(f"\n📋 Phase 1: Scraper Selection")
        Actor.log.info(f"Target: {input_data['target']}")

        # Initialize Apify client
        apify_client = ApifyClient(input_data['apify_token'])

        # Find and select best scrapers (banned filter applied)
        selected_scrapers, target_type = await find_and_select_scrapers(
            apify_client=apify_client,
            target=input_data['target'],
            budget_mode=input_data.get('scraper_budget', 'optimal'),
            top_n=3  # Primary + 2 fallbacks
        )

        Actor.log.info(f"Target type: {target_type}")
        Actor.log.info(f"Selected {len(selected_scrapers)} scrapers (with fallbacks)")

        # ========== PHASE 2: SCRAPE WITH FALLBACK ==========

        Actor.log.info(f"\n🕷️  Phase 2: Web Scraping")

        scrape_result = await execute_scraper_with_fallback(
            apify_client=apify_client,
            selected_scrapers=selected_scrapers,
            target=input_data['target'],
            max_pages=input_data.get('max_pages', 100)
        )

        if not scrape_result['success']:
            raise RuntimeError(f"All scrapers failed: {scrape_result['errors']}")

        scraped_items = scrape_result['data']
        scraper_used = scrape_result['scraper_used']

        Actor.log.info(f"✅ Scraped {len(scraped_items)} pages using {scraper_used}")

        # ========== PHASE 3: DOCUMENT CONVERSION ==========

        Actor.log.info(f"\n📄 Phase 3: Document Conversion")

        documents = convert_dataset_to_documents(
            dataset_items=scraped_items,
            output_dir=docs_dir,
            url_field='url',
            html_field='html'
        )

        if not documents:
            raise RuntimeError("No valid documents created from scraped data")

        Actor.log.info(f"✅ Created {len(documents)} documents")

        # Calculate indexing cost estimate
        indexing_cost = calculate_indexing_cost(documents)

        # ========== PHASE 4: UPLOAD TO GEMINI ==========

        Actor.log.info(f"\n🧠 Phase 4: Gemini File Search Upload")

        gemini_corpus = await upload_to_gemini(
            gemini_api_key=input_data['gemini_api_key'],
            document_paths=documents,
            corpus_name=input_data.get('corpus_name', 'scraped-knowledge')
        )

        Actor.log.info(f"✅ Knowledge base ready!")
        Actor.log.info(f"   Store: {gemini_corpus['file_search_store_name']}")
        Actor.log.info(f"   Files: {gemini_corpus['files_indexed']}")
        Actor.log.info(f"   Cost: ${gemini_corpus['cost_estimate_usd']:.4f}")

        # ========== PHASE 5: PRICING (PER-PAGE MODEL) ==========

        Actor.log.info(f"\n💰 Phase 5: Per-Page Charging")

        # Charge per page processed (pay-per-event)
        pages_count = len(scraped_items)
        price_per_page = 0.0025  # Base price, Store discounts applied automatically

        Actor.log.info(f"  Pages indexed: {pages_count}")
        Actor.log.info(f"  Base price: ${price_per_page}/page")
        Actor.log.info(f"  Estimated cost: ${0.02 + (pages_count * price_per_page):.2f}")
        Actor.log.info(f"  (Includes ~$0.02 actor start + ${pages_count * price_per_page:.2f} for pages)")
        Actor.log.info(f"  💡 Store discounts apply automatically based on your Apify plan")

        # Charge for each page processed (Apify applies Store discounts automatically)
        if pages_count > 0:
            await Actor.charge(event_name='page-processed', count=pages_count)

        # ========== PHASE 6: OUTPUT ==========

        Actor.log.info(f"\n📤 Phase 6: Generate Output")

        # Generate query guide
        query_guide_path = workspace / "query-guide.md"
        generate_query_guide(
            corpus_metadata=gemini_corpus,
            output_path=query_guide_path
        )

        # Read query guide content
        query_guide_content = query_guide_path.read_text()

        # Save query guide to key-value store (for output schema)
        await Actor.set_value('QUERY_GUIDE.md', query_guide_content, content_type='text/markdown')

        # Save to dataset (structured data)
        await Actor.push_data({
            'target': input_data['target'],
            'target_type': target_type,
            'scraper_used': scraper_used,
            'pages_scraped': len(scraped_items),
            'documents_created': len(documents),
            'gemini_corpus': {
                'file_search_store_name': gemini_corpus['file_search_store_name'],
                'corpus_name': input_data.get('corpus_name', 'scraped-knowledge'),
                'files_indexed': gemini_corpus['files_indexed'],
                'storage_type': gemini_corpus['storage_type'],
                'storage_persistence': gemini_corpus['storage_persistence'],
                'globally_accessible': gemini_corpus['globally_accessible'],
                'estimated_tokens': gemini_corpus['estimated_tokens'],
                'cost_estimate_usd': gemini_corpus['cost_estimate_usd']
            },
            'pricing': {
                'model': 'pay-per-page',
                'pages_processed': pages_count,
                'price_per_page': price_per_page,
                'start_fee': 0.02,
                'estimated_total': round(0.02 + (pages_count * price_per_page), 2),
                'note': 'Store discounts applied automatically based on your Apify plan'
            },
            'created_at': gemini_corpus['created_at'],
            'query_instructions': 'See query-guide.md in Key-Value Store for detailed usage instructions'
        })

        # Note: Query guide already saved to KV Store at line 270 as QUERY_GUIDE.md

        # Save corpus metadata to KV Store for reference
        await Actor.set_value('gemini-corpus.json', gemini_corpus)

        # ========== SUCCESS ==========

        Actor.log.info(f"\n🎉 SUCCESS!")
        Actor.log.info(f"")
        Actor.log.info(f"Knowledge base created: {gemini_corpus['file_search_store_name']}")
        Actor.log.info(f"Files indexed: {gemini_corpus['files_indexed']}")
        Actor.log.info(f"Pages processed: {pages_count} × ${price_per_page} = ${pages_count * price_per_page:.2f}")
        Actor.log.info(f"")
        Actor.log.info(f"📖 See 'query-guide.md' in Key-Value Store for usage instructions")
        Actor.log.info(f"")
        Actor.log.info(f"💡 Your knowledge base is ready to query from:")
        Actor.log.info(f"   - Python SDK (any device)")
        Actor.log.info(f"   - Google AI Studio (web)")
        Actor.log.info(f"   - Gemini mobile apps (iOS/Android)")
        Actor.log.info(f"")
        Actor.log.info(f"💰 Query costs: ~$0.001 each (essentially free)")


if __name__ == '__main__':
    asyncio.run(main())
