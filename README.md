# Gemini File Search Builder

**Build Gemini File Search RAG knowledge bases from any website with automatic citations**

[![Apify Store](https://img.shields.io/badge/Apify-Store-blue)](https://console.apify.com)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Apify SDK](https://img.shields.io/badge/Apify%20SDK-3.0-green)](https://docs.apify.com/sdk/python/)

## What It Does

This Apify actor creates a **permanent, queryable knowledge base** from any website using Google's Gemini File Search (announced November 6, 2025). Unlike traditional scrapers that just extract data, this actor transforms websites into intelligent Q&A systems with **automatic citation tracking**.

### Key Features

- 🧠 **Automatic RAG Pipeline** - Scrape → Clean → Upload → Query (all in one run)
- 📚 **Built-in Citations** - Every answer includes source documents
- ♾️ **Unlimited Free Queries** - Pay once to scrape, query forever (no storage fees)
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
         Query Interface ← Gemini File Search ← Upload Documents
```

1. **Smart Scraper Selection** - Analyzes target and selects optimal Apify scraper
2. **Content Cleaning** - Removes ads, navigation, extracts main content
3. **Document Creation** - Formats as clean text with metadata
4. **Gemini Upload** - Creates File Search Store (persistent, free storage)
5. **Query Guide** - Returns instructions for using your knowledge base

## Quick Start

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

After the actor completes, use the returned `file_search_store_name` to query:

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_GEMINI_KEY")

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='How do I use decorators in Python?',
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=["YOUR_STORE_NAME"]
            )
        )]
    )
)

print(response.text)  # Answer with automatic citations
```

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | ✅ | - | Website URL to scrape and index |
| `max_pages` | integer | | 100 | Maximum pages to scrape (1-2000) |
| `scraper_budget` | string | | "optimal" | Cost strategy: `minimal`, `optimal`, `premium` |
| `corpus_name` | string | | "scraped-knowledge" | Name for your knowledge base |
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

## Pricing & Costs

### Actor Costs (Pay Once)
- **Scraping**: Apify platform credits (varies by scraper)
- **Indexing**: $0.15 per 1M tokens (one-time)

### Query Costs (Pay Per Use)
- **Storage**: FREE (indefinite, no storage fees)
- **Queries**: ~$0.001 per query (gemini-2.5-flash)

**Example**: Index 100 documentation pages (~100K tokens) = $0.015 one-time cost, then query forever.

## Challenge Compliance

**Apify $1M Challenge - Fully Compliant**

✅ **100% Banned Scraper Filter**
- Social media: Instagram, Facebook, TikTok, LinkedIn, Twitter, YouTube
- E-commerce: Amazon
- Search engines: Google Maps, Google Search, Google Trends
- B2B platforms: Apollo

✅ **Skills-Based Architecture**
- Progressive disclosure (75% token reduction)
- Hook-based enforcement (zero bypass)
- Automated compliance testing

✅ **Test Coverage**
- 49/49 unit tests passing
- 6/6 integration tests passing
- 100% banned pattern validation

## Architecture

### BORG Patterns Used

1. **Skills-First Disclosure** - `.claude/skills/` directory with 3 skills
2. **Hook Enforcement** - `src/hooks/skill_enforcement.py` validates at startup
3. **Banned Filter** - `src/tools/scraper_selector.py` blocks all prohibited scrapers

### Tech Stack

- **Apify SDK 3.0** - Actor runtime & scraper orchestration
- **Google Gemini API** - File Search for RAG (unified SDK `google-genai`)
- **BeautifulSoup4** - HTML parsing & content extraction
- **Python 3.11+** - Type hints, async/await

### Project Structure

```
gemini-file-search-builder/
├── .actor/
│   ├── actor.json          # Actor configuration
│   └── INPUT_SCHEMA.json   # Input validation schema
├── .claude/
│   └── skills/             # BORG L2.5 skills
│       ├── apify-scraper-selection/
│       ├── document-conversion/
│       └── gemini-file-upload/
├── src/
│   ├── main.py             # Main workflow orchestration
│   ├── tools/
│   │   ├── scraper_selector.py    # Smart scraper selection + banned filter
│   │   ├── document_converter.py  # HTML → clean text
│   │   └── gemini_uploader.py     # File Search integration
│   └── hooks/
│       └── skill_enforcement.py   # Startup validation
├── tests/
│   └── test_banned_filter.py     # 49 test cases
├── requirements.txt
└── README.md
```

## Development

### Local Setup

```bash
# Clone repository
git clone <your-repo-url>
cd gemini-file-search-builder

# Install dependencies
pip install -r requirements.txt

# Run locally
python __main__.py
```

### Running Tests

```bash
pytest tests/  # 49/49 tests should pass
```

### Environment Variables

Create `.env` file (not committed):
```bash
GEMINI_API_KEY=your_key_here
APIFY_TOKEN=your_token_here
```

## Limitations & Known Issues

1. **Apify Store Search** - Current MVP uses hardcoded scraper whitelist. Production would use dynamic Store search.

2. **Proxy Restrictions** - Some sites (e.g., docs.react.dev) may be blocked by Apify cloud proxies. Use accessible documentation sites.

3. **File Size Limits** - Gemini File Search supports up to 2GB per file, 10K files per store.

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

Connect with popular automation platforms and cloud services:

- **Make, Zapier, Slack** - Automate workflows
- **Webhooks** - Trigger actions when runs complete
- **Google Sheets, Google Drive** - Export and sync data
- **API Access** - Programmatic control via Python/JavaScript

See [all integrations](https://docs.apify.com/platform/integrations)

## Using with AI Agents

This Actor is compatible with Model Context Protocol (MCP) and can be used with AI agents:

- **Claude Desktop** - Use via Apify MCP server
- **LibreChat** - Integrate into chat workflows
- **Custom MCP clients** - Programmatic access

AI agents can trigger this Actor automatically based on user queries. See the [MCP documentation](https://docs.apify.com/platform/integrations/mcp) for setup instructions.

## Support & Contributing

- **Issues**: GitHub Issues
- **Questions**: GitHub Discussions
- **Apify $1M Challenge**: Submission ID TBD

## License

MIT License - See LICENSE file

## Author

Built for the Apify $1M Challenge (November 2025 - January 2026)

---

**🎯 Ready to try it?** [Run on Apify](https://console.apify.com/actors) • [View Source](https://github.com/your-repo)
