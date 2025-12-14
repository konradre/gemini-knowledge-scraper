# Gemini File Search Builder

**Turn any website into an AI-powered knowledge base with Google Gemini. Get unlimited queries with automatic citations.**

## What You Get

Scrape once, query forever. This actor builds permanent Gemini File Search RAG knowledge bases from any website. After initial indexing costs (actor + scraper + Gemini), storage and queries are free indefinitely.

**Perfect for:**
- Creating AI chatbots from documentation
- Building searchable knowledge bases
- Powering RAG applications with website content
- Querying technical docs with natural language

**Key benefits:**
- ✅ **One-time scraping** - Actor fee: $0.0015/page (plus Apify scraper + Gemini costs)
- ✅ **Automatic citations** - Every answer includes sources
- ✅ **No storage fees** - Gemini File Search storage is free and persistent
- ✅ **Cross-platform** - Query from Python, web, or mobile
- ✅ **Challenge compliant** - 100% banned scraper filtering

### Key Features

- 🧠 **Automatic RAG Pipeline** - Scrape → Clean → Upload to Gemini (all in one run)
- 📚 **Built-in Citations** - Every answer includes source documents
- ♾️ **Unlimited Free Queries** - After initial indexing, query forever at no additional cost
- 🎯 **Challenge Compliant** - 100% banned scraper filtering (Instagram, Amazon, Google Maps, etc.)
- 🚀 **Zero Setup** - Just provide URL + Gemini API key
- 💰 **Cost Optimized** - Smart scraper selection based on your budget
- 🎨 **Multiple Output Formats** - Supports Markdown, HTML, and plain text extraction

## Use Cases

- **Documentation Indexing** - Convert technical docs into queryable knowledge bases
- **Research Databases** - Create searchable archives from academic sites
- **Content Libraries** - Index blog posts, articles, tutorials
- **Internal Wikis** - Transform company knowledge bases for AI access

## How It Works

```
Website URL → Scraper Selection → Content Extraction → Document Conversion
                                                              ↓
                                        Gemini File Search ← Upload Documents
                                                              ↓
                                        Queryable Knowledge Base (You query it later)
```

1. **Smart Scraper Selection** - Analyzes target and selects optimal Apify scraper
2. **Content Cleaning** - Removes ads, navigation, extracts main content
3. **Document Creation** - Formats as clean text with metadata
4. **Gemini Upload** - Creates File Search Store (persistent, free storage)
5. **Query Guide** - Returns instructions for using your knowledge base

## How to Build a Gemini Knowledge Base (3 Steps)

### 1. Get API Keys

**Gemini API Key** (required):
- Visit https://aistudio.google.com/apikey
- Create new API key (free tier available)
- ⚠️ **Important:** Use the SAME key you'll use to query the knowledge base later. File Search Stores are tied to the creating API key.

**Apify Token** (required):
- Visit https://console.apify.com/settings/integrations
- Copy your API token

### 2. Run the Actor

```json
{
  "target": "https://docs.python.org",
  "max_pages": 100,
  "scraper_budget": "optimal",
  "corpus_name": "python-docs",
  "gemini_api_key": "YOUR_GEMINI_KEY",
  "apify_token": "YOUR_APIFY_TOKEN"
}
```

### 3. Query Your Knowledge Base

After the actor completes, query your knowledge base using:
- **Google AI Studio** (web interface - easiest)
- **Python SDK** (for developers)
- **Gemini mobile apps** (iOS/Android)

**Python example:**
```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_GEMINI_KEY")

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Your question here',
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=["YOUR_STORE_NAME"]
            )
        )]
    )
)

print(response.text)  # Answer with citations
```

**See the query guide in your run's Key-Value Store for complete instructions.**

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | ✅ | - | Website URL to scrape and index |
| `max_pages` | integer | | 10 | Maximum pages to scrape (1-2000) |
| `scraper_budget` | string | | "optimal" | Cost strategy: `minimal`, `optimal`, `premium` |
| `corpus_name` | string | ✅ | - | Unique name for your knowledge base |
| `gemini_api_key` | string | ✅ | - | Google Gemini API key |
| `apify_token` | string | ✅ | - | Apify API token |

## Output

```json
{
  "file_search_store_name": "fileSearchStores/pythondocs-abc123",
  "files_indexed": 150,
  "total_size_mb": 2.5,
  "estimated_tokens": 125000,
  "indexing_cost_usd": 0.0188,
  "storage_type": "File Search Store",
  "storage_persistence": "Indefinite (free)",
  "query_cost_estimate": "$0.001 per query",
  "query_guide_url": "https://docs.google.com/..."
}
```

## How Much Does It Cost?

**IMPORTANT:** The total cost includes THREE separate components billed by different services:

### 1. Actor Fees (Charged by This Actor)

This Actor uses **pay-per-page pricing**:

- **Actor start**: $0.02 per run (one-time)
- **Page processed**: $0.0015 per page (base price)

**Store Discount Tiers** - Your Apify subscription plan determines automatic discounts:

| Plan | Monthly Cost | Discount | Actor Price/Page | Actor Cost (100 Pages) |
|------|--------------|----------|------------------|------------------------|
| **Free** | $0 | 0% | $0.0015 | **$0.17** |
| **Starter** | $39 | 10% (BRONZE) | $0.00135 | **$0.155** |
| **Scale** | $199 | 20% (SILVER) | $0.0012 | **$0.14** |
| **Business** | $999 | 30% (GOLD) | $0.00105 | **$0.125** |

💰 **Upgrade your Apify plan to save up to 30% on actor fees!**

### 2. Apify Scraper Costs (Charged by Apify Platform)

The actor uses Apify scrapers to extract content. **You pay Apify separately** for:
- Scraper compute time (varies by scraper and site complexity)
- Typical cost: **$0.001-0.01 per page** (depends on scraper_budget setting)
- Billed from your Apify platform credits

**Example for 100 pages:**
- Minimal budget: ~$0.10 (simple HTML scrapers)
- Optimal budget: ~$0.50 (balanced performance)
- Premium budget: ~$1.00+ (advanced AI scrapers)

### 3. Gemini API Costs (Charged by Google)

Google charges for **document indexing** when uploading to File Search:
- **Indexing**: ~$0.15 per 1 million tokens (~$0.01-0.10 for typical 100-page sites)
- **Storage**: FREE (indefinite, no ongoing fees)
- **Query embeddings**: FREE (unlimited queries after indexing)

See [Gemini pricing](https://ai.google.dev/pricing) for current rates.

### Total Cost Example (100 Pages)

| Component | Cost (Typical) |
|-----------|----------------|
| Actor fee (FREE tier) | $0.17 |
| Apify scraper (optimal) | ~$0.50 |
| Gemini indexing | ~$0.05 |
| **TOTAL** | **~$0.72** |

**After indexing:** Query unlimited times at $0 additional cost.

### What You DON'T Pay to This Actor

✅ **Apify scraper costs** - Billed separately by Apify platform (from your credits)
✅ **Gemini API costs** - Billed separately by Google (from your Gemini API key)
✅ **Pass-through fees** - No markup; you pay Apify and Google directly

### Comparison

- **10x cheaper** than premium AI collectors ($0.0025 vs $0.25/page)
- **Gemini-optimized** vs generic scrapers
- **Transparent billing** - Only successful pages charged

## Challenge Compliance

**Apify $1M Challenge - Fully Compliant**

✅ **100% Banned Scraper Filter**
- Social media: Instagram, Facebook, TikTok, LinkedIn, Twitter, YouTube
- E-commerce: Amazon
- Search engines: Google Maps, Google Search, Google Trends
- B2B platforms: Apollo

✅ **Quality Assurance**
- 49/49 unit tests passing
- Production-tested on real websites
- Automatic fallback system for reliability

## FAQ

**Q: How long does the knowledge base persist?**
A: Indefinitely (until manually deleted). No storage expiration or fees.

**Q: Can I update the knowledge base later?**
A: Yes! Upload additional documents to the same File Search Store.

**Q: What's the maximum site size?**
A: Up to 2,000 pages (configurable), ~2GB total content.

**Q: Do I need a Google Cloud account?**
A: No! Just a Gemini API key from aistudio.google.com (free tier available).

**Q: Can I use a different API key to query the knowledge base?**
A: No. File Search Stores are tied to the API key that created them. You must use the SAME Gemini API key for both creating and querying the knowledge base. This ensures your data remains private and accessible only to you.

**Q: How accurate are the citations?**
A: Gemini File Search automatically cites source documents with chunk-level precision.

**Q: Is web scraping legal?**
A: Web scraping is generally legal for publicly available, non-personal data. Always respect robots.txt and website terms of service. For personal data, ensure GDPR compliance. Consult legal counsel if unsure. Learn more: [Is web scraping legal?](https://blog.apify.com/is-web-scraping-legal/)

## Integrations

This Actor works seamlessly with Apify's platform integrations:

- **Make, Zapier** - Automate workflows with no-code tools
- **Webhooks** - Trigger actions when knowledge base creation completes
- **API Access** - Control programmatically via Python/JavaScript SDKs
- **Scheduled Runs** - Automatically update knowledge bases on schedule

All Apify actors support these integrations out of the box. See [Apify integrations](https://docs.apify.com/platform/integrations) for setup guides.

## Using with AI Agents

This Actor is compatible with Model Context Protocol (MCP) and can be used with AI agents:

- **Claude Desktop** - Use via Apify MCP server
- **LibreChat** - Integrate into chat workflows
- **Custom MCP clients** - Programmatic access

AI agents can trigger this Actor automatically based on user queries. See the [MCP documentation](https://docs.apify.com/platform/integrations/mcp) for setup instructions.

## Support

**Need help?**
- Use the **Issues** tab above to report problems or request features
- Check the **FAQ** section for common questions
- Contact via Apify messaging for urgent issues

**Built for the Apify $1M Challenge** (November 2025 - January 2026)
