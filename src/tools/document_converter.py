"""
Document Conversion Module for Gemini Knowledge Scraper

Converts scraped HTML/JSON data into clean text documents suitable for Gemini File Search.

Key functions:
- HTML → Text extraction (BeautifulSoup)
- Metadata header generation (source, date, title)
- Text cleaning (remove noise, normalize whitespace)
- Document formatting for optimal RAG indexing
"""

from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import re


def clean_html_text(html: str) -> str:
    """
    Extract clean text from HTML using BeautifulSoup.

    Removes:
    - Script tags
    - Style tags
    - Navigation elements
    - Footer elements
    - Advertisements

    Args:
        html: Raw HTML string

    Returns:
        Clean text string with normalized whitespace
    """
    # Parse HTML
    soup = BeautifulSoup(html, 'lxml')

    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'noscript']):
        element.decompose()

    # Remove common ad/tracking classes
    ad_patterns = [
        'advertisement', 'ads', 'ad-container', 'sponsored',
        'tracking', 'analytics', 'cookie-banner', 'popup'
    ]
    for pattern in ad_patterns:
        for element in soup.find_all(class_=re.compile(pattern, re.I)):
            element.decompose()

    # Extract text
    text = soup.get_text(separator='\n', strip=True)

    # Clean whitespace
    text = normalize_whitespace(text)

    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    - Replace tabs with spaces
    - Collapse multiple spaces to single space
    - Collapse multiple newlines to max 2
    - Strip trailing whitespace per line

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    # Replace tabs with spaces
    text = text.replace('\t', ' ')

    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split('\n')]

    # Collapse multiple spaces within lines
    lines = [re.sub(r' +', ' ', line) for line in lines]

    # Collapse multiple blank lines (max 2 newlines = 1 blank line)
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def extract_title(html: str, url: str) -> str:
    """
    Extract page title from HTML.

    Priority:
    1. <title> tag
    2. <h1> tag
    3. <meta property="og:title">
    4. URL basename as fallback

    Args:
        html: Raw HTML string
        url: Source URL (for fallback)

    Returns:
        Page title
    """
    soup = BeautifulSoup(html, 'lxml')

    # Try <title>
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # Try <h1>
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)

    # Try Open Graph title
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title['content'].strip()

    # Fallback: URL basename
    from urllib.parse import urlparse
    path = urlparse(url).path
    basename = path.rstrip('/').split('/')[-1]
    return basename.replace('-', ' ').replace('_', ' ').title() if basename else 'Untitled'


def create_metadata_header(
    url: str,
    title: str,
    scraped_at: Optional[datetime] = None
) -> str:
    """
    Create metadata header for document.

    Format:
    ---
    Source: <url>
    Title: <title>
    Scraped: <timestamp>
    ---

    Args:
        url: Source URL
        title: Page title
        scraped_at: Scrape timestamp (defaults to now)

    Returns:
        Formatted metadata header
    """
    if scraped_at is None:
        scraped_at = datetime.now()

    header = f"""---
Source: {url}
Title: {title}
Scraped: {scraped_at.isoformat()}
---

"""
    return header


def convert_html_to_document(
    html: str,
    url: str,
    output_path: Path,
    include_metadata: bool = True
) -> Path:
    """
    Convert HTML to a clean text document suitable for Gemini indexing.

    Workflow:
    1. Extract title
    2. Clean HTML → text
    3. Add metadata header (if enabled)
    4. Save to file

    Args:
        html: Raw HTML string
        url: Source URL
        output_path: Where to save the document
        include_metadata: Whether to add metadata header

    Returns:
        Path to created document

    Side effects:
        Creates file at output_path
    """
    # Extract title
    title = extract_title(html, url)

    # Clean HTML
    clean_text = clean_html_text(html)

    # Build document
    if include_metadata:
        header = create_metadata_header(url, title)
        document = header + clean_text
    else:
        document = clean_text

    # Save to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding='utf-8')

    return output_path


def convert_dataset_to_documents(
    dataset_items: List[Dict],
    output_dir: Path,
    url_field: str = 'url',
    html_field: str = 'html'
) -> List[Path]:
    """
    Convert Apify dataset items to documents.

    Apify scrapers return datasets (list of dicts) with HTML/text content.
    This function converts each item to a clean text document.

    Args:
        dataset_items: List of items from Apify dataset
        output_dir: Directory to save documents
        url_field: Field name containing URL
        html_field: Field name containing HTML

    Returns:
        List of paths to created documents

    Example dataset item:
        {
            "url": "https://example.com/page1",
            "html": "<html>...</html>",
            "title": "Example Page",
            ...
        }
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    created_docs = []

    for i, item in enumerate(dataset_items):
        url = item.get(url_field, f'unknown-{i}')

        # Try multiple field names (different scrapers use different fields)
        html = (
            item.get(html_field, '') or           # Default field
            item.get('html', '') or                # Standard HTML field
            item.get('text', '') or                # Text content field
            item.get('markdown', '') or            # Markdown field
            item.get('content', '') or             # Generic content field
            item.get('crawl', {}).get('html', '')  # Nested HTML field
        )

        if not html:
            print(f"⚠️  Skipping {url} - no content in any field (tried: {html_field}, html, text, markdown, content, crawl.html)")
            continue

        # Generate filename from index
        filename = f"doc_{i:04d}.txt"
        output_path = output_dir / filename

        # Convert
        doc_path = convert_html_to_document(
            html=html,
            url=url,
            output_path=output_path,
            include_metadata=True
        )

        created_docs.append(doc_path)
        print(f"✅ Converted: {url} → {filename}")

    print(f"\n📄 Created {len(created_docs)} documents in {output_dir}")
    return created_docs


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text (rough approximation).

    Rule of thumb:
    - English: ~4 characters per token
    - Technical docs: ~5 characters per token (more jargon)

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    # Use conservative estimate (5 chars per token for technical content)
    return len(text) // 5


def calculate_indexing_cost(documents: List[Path]) -> float:
    """
    Calculate estimated Gemini indexing cost.

    Pricing:
    - Indexing: $0.15 per 1M tokens (one-time)

    Args:
        documents: List of document paths

    Returns:
        Estimated cost in USD
    """
    total_tokens = 0

    for doc_path in documents:
        text = doc_path.read_text(encoding='utf-8')
        tokens = estimate_tokens(text)
        total_tokens += tokens

    # Calculate cost
    cost_per_million = 0.15
    cost = (total_tokens / 1_000_000) * cost_per_million

    print(f"\n💰 Indexing cost estimate:")
    print(f"   Total tokens: {total_tokens:,}")
    print(f"   Cost: ${cost:.4f} (${cost_per_million}/1M tokens)")

    return cost


# ========== HELPER FUNCTIONS ==========

def extract_main_content(html: str) -> str:
    """
    Try to extract main content area (heuristic-based).

    Looks for:
    - <main> tag
    - <article> tag
    - <div class="content"> or similar

    Fallback to full body if not found.

    Args:
        html: Raw HTML

    Returns:
        Main content HTML (subset of input)
    """
    soup = BeautifulSoup(html, 'lxml')

    # Try semantic tags
    main = soup.find('main')
    if main:
        return str(main)

    article = soup.find('article')
    if article:
        return str(article)

    # Try common content class names
    content_patterns = [
        'content', 'main-content', 'article-content',
        'post-content', 'entry-content', 'documentation'
    ]
    for pattern in content_patterns:
        content = soup.find(class_=re.compile(pattern, re.I))
        if content:
            return str(content)

    # Fallback: body
    body = soup.find('body')
    return str(body) if body else html


def split_long_document(
    text: str,
    max_tokens: int = 10000,
    overlap: int = 500
) -> List[str]:
    """
    Split a long document into chunks (if needed for very large docs).

    Gemini File Search handles chunking automatically, but for very large
    documents (>50K tokens), pre-splitting can improve quality.

    Args:
        text: Input text
        max_tokens: Maximum tokens per chunk
        overlap: Token overlap between chunks (for context continuity)

    Returns:
        List of text chunks
    """
    estimated_tokens = estimate_tokens(text)

    # No split needed
    if estimated_tokens <= max_tokens:
        return [text]

    # Split on paragraphs (preserves structure)
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunks.append('\n\n'.join(current_chunk))

            # Start new chunk with overlap (last few paragraphs)
            overlap_paras = []
            overlap_tokens = 0
            for prev_para in reversed(current_chunk):
                prev_tokens = estimate_tokens(prev_para)
                if overlap_tokens + prev_tokens <= overlap:
                    overlap_paras.insert(0, prev_para)
                    overlap_tokens += prev_tokens
                else:
                    break

            current_chunk = overlap_paras
            current_tokens = overlap_tokens

        current_chunk.append(para)
        current_tokens += para_tokens

    # Add final chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    print(f"📚 Split document into {len(chunks)} chunks ({estimated_tokens:,} tokens)")
    return chunks
