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

            # Run scraper with document download enabled
            run = apify_client.actor(scraper_id).call(
                run_input={
                    'startUrls': [{'url': target}],
                    'maxCrawlPages': max_pages,  # Fixed parameter name
                    'maxConcurrency': 5,
                    'saveFiles': True,  # Download PDFs, DOCX, XLSX, etc.
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
                    'defaultKeyValueStoreId': run.get('defaultKeyValueStoreId'),
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
        kv_store_id = scrape_result.get('defaultKeyValueStoreId')

        Actor.log.info(f"✅ Scraped {len(scraped_items)} pages using {scraper_used}")

        # ========== PHASE 2.5: DOWNLOAD FILES FROM SCRAPER ==========

        downloaded_files = []
        if kv_store_id:
            Actor.log.info(f"\n📥 Checking for downloaded files (PDFs, DOCX, etc.)...")

            # Check KV store for downloaded files
            kv_client = apify_client.key_value_store(kv_store_id)

            # Look for file items in dataset
            file_items = [item for item in scraped_items if item.get('type') == 'file']

            if file_items:
                Actor.log.info(f"   Found {len(file_items)} downloaded documents")

                for file_item in file_items:
                    file_url = file_item.get('fileUrl')
                    if file_url:
                        # Extract filename from URL
                        filename = file_url.split('/')[-1]
                        file_path = docs_dir / filename

                        try:
                            # Download file from KV store
                            file_record = kv_client.get_record(filename)
                            if file_record and file_record.get('value'):
                                file_path.write_bytes(file_record['value'])
                                downloaded_files.append(file_path)
                                Actor.log.info(f"   ✅ Downloaded: {filename}")
                        except Exception as e:
                            Actor.log.warning(f"   ⚠️  Failed to download {filename}: {e}")
            else:
                Actor.log.info(f"   No downloadable files found")

        # ========== PHASE 3: DOCUMENT CONVERSION ==========

        Actor.log.info(f"\n📄 Phase 3: Document Conversion")

        documents = convert_dataset_to_documents(
            dataset_items=scraped_items,
            output_dir=docs_dir,
            url_field='url',
            html_field='html'
        )

        if not documents and not downloaded_files:
            raise RuntimeError("No valid documents created from scraped data")

        # Combine text documents + downloaded files for Gemini upload
        all_documents = documents + downloaded_files

        Actor.log.info(f"✅ Prepared {len(all_documents)} documents for indexing:")
        Actor.log.info(f"   - Text documents: {len(documents)}")
        Actor.log.info(f"   - Downloaded files (PDF/DOCX/etc): {len(downloaded_files)}")

        # Calculate indexing cost estimate (text documents only for now)
        if documents:
            indexing_cost = calculate_indexing_cost(documents)

        # ========== PHASE 4: UPLOAD TO GEMINI ==========

        Actor.log.info(f"\n🧠 Phase 4: Gemini File Search Upload")

        gemini_corpus = await upload_to_gemini(
            gemini_api_key=input_data['gemini_api_key'],
            document_paths=all_documents,  # Upload both text AND binary files
            corpus_name=input_data.get('corpus_name', 'scraped-knowledge')
        )

        Actor.log.info(f"✅ Knowledge base ready!")
        Actor.log.info(f"   Store: {gemini_corpus['file_search_store_name']}")
        Actor.log.info(f"   Files: {gemini_corpus['files_indexed']}")
        Actor.log.info(f"   Cost: ${gemini_corpus['cost_estimate_usd']:.4f}")

        # ========== PHASE 5: PRICING ==========

        Actor.log.info(f"\n💰 Phase 5: Calculate Pricing")

        # Determine tier based on pages scraped
        pages_count = len(scraped_items)
        if pages_count <= 50:
            tier = 'small'
            tier_price = 8.00
            event_name = 'knowledge-base-small'
        elif pages_count <= 200:
            tier = 'medium'
            tier_price = 12.00
            event_name = 'knowledge-base-medium'
        else:
            tier = 'large'
            tier_price = 18.00
            event_name = 'knowledge-base-large'

        Actor.log.info(f"Pricing tier: {tier.upper()}")
        Actor.log.info(f"  Pages scraped: {pages_count}")
        Actor.log.info(f"  Tier price: ${tier_price:.2f}")
        Actor.log.info(f"  Gemini indexing cost: ${gemini_corpus['cost_estimate_usd']:.4f}")
        Actor.log.info(f"  Total charge: ${tier_price:.2f}")

        # Charge user based on tier (pay-per-event pricing)
        await Actor.charge(event_name=event_name, count=1)

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
                'tier': tier,
                'tier_price': tier_price,
                'pages_count': pages_count,
                'gemini_indexing_cost': gemini_corpus['cost_estimate_usd'],
                'event_charged': event_name
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
        Actor.log.info(f"Tier: {tier.upper()} (${tier_price:.2f})")
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
