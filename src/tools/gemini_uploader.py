"""
Gemini File Search Uploader for Gemini Knowledge Scraper

CRITICAL: Uses File Search Stores (indefinite storage)
NOT basic File API (which deletes after 48 hours)

Key functions:
- Create File Search Store (persistent container)
- Upload documents to store
- Wait for import completion
- Return store name for global access

Documentation:
- File Search Stores: https://ai.google.dev/gemini-api/docs/file-search
- Persistence: Indefinite (until manually deleted)
- Storage: Free (no storage fees)
- Queries: Free (only pay for generation ~$0.001/query)
"""

from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import asyncio
from google import genai
from google.genai import types


async def create_file_search_store(
    client: genai.Client,
    store_name: str,
    display_name: Optional[str] = None
) -> str:
    """
    Create a File Search Store (persistent knowledge base container).

    CRITICAL: This is NOT the basic File API.
    File Search Stores persist indefinitely (until manually deleted).

    Args:
        client: Initialized Gemini client
        store_name: Internal store name (for your reference)
        display_name: Human-readable name (shown in AI Studio)

    Returns:
        Store resource name (format: "fileSearchStores/<id>")

    Example:
        >>> client = genai.Client(api_key="...")
        >>> store_name = await create_file_search_store(client, "react-docs")
        >>> print(store_name)
        fileSearchStores/abc123xyz
    """
    if display_name is None:
        display_name = store_name

    # Create File Search Store
    file_search_store = client.file_search_stores.create(
        config={'display_name': display_name}
    )

    print(f"✅ Created File Search Store: {file_search_store.name}")
    print(f"   Display name: {display_name}")
    print(f"   Persistence: Indefinite (until manually deleted)")

    return file_search_store.name


async def upload_documents_to_store(
    client: genai.Client,
    store_name: str,
    document_paths: List[Path],
    max_wait: int = 300
) -> List[Dict]:
    """
    Upload documents to a File Search Store.

    CRITICAL: Uses upload_to_file_search_store (persistent)
    NOT files.upload (which deletes after 48h)

    Workflow:
    1. Upload each document to the store
    2. Wait for import operations to complete
    3. Return metadata for uploaded files

    Args:
        client: Initialized Gemini client
        store_name: File Search Store name (from create_file_search_store)
        document_paths: List of document file paths
        max_wait: Maximum seconds to wait per file (default: 300s)

    Returns:
        List of uploaded file metadata dicts

    Raises:
        TimeoutError: If import takes longer than max_wait
        RuntimeError: If import fails
    """
    uploaded_files = []

    print(f"\n📤 Uploading {len(document_paths)} documents to {store_name}...")

    for i, doc_path in enumerate(document_paths, 1):
        print(f"   [{i}/{len(document_paths)}] Uploading {doc_path.name}...")

        # Upload to File Search Store (NOT basic files.upload!)
        operation = client.file_search_stores.upload_to_file_search_store(
            file=str(doc_path),
            file_search_store_name=store_name,
            config={
                'display_name': doc_path.name,
                'custom_metadata': [
                    {'key': 'source_path', 'string_value': str(doc_path)},
                    {'key': 'upload_date', 'string_value': datetime.now().isoformat()},
                    {'key': 'file_size', 'string_value': str(doc_path.stat().st_size)}
                ]
            }
        )

        # Wait for import to complete
        waited = 0
        while not operation.done and waited < max_wait:
            await asyncio.sleep(2)
            operation = client.operations.get(operation)
            waited += 2

            if waited % 10 == 0:  # Progress update every 10s
                print(f"      Importing... ({waited}s elapsed)")

        if not operation.done:
            raise TimeoutError(f"Import timeout for {doc_path.name} after {max_wait}s")

        if operation.error:
            raise RuntimeError(f"Import failed for {doc_path.name}: {operation.error}")

        # Extract file metadata from operation result
        file_metadata = {
            'name': doc_path.name,
            'path': str(doc_path),
            'size': doc_path.stat().st_size,
            'imported_at': datetime.now().isoformat()
        }

        uploaded_files.append(file_metadata)
        print(f"      ✅ Imported successfully")

    print(f"\n✅ All {len(uploaded_files)} documents uploaded and imported")
    return uploaded_files


async def upload_to_gemini(
    gemini_api_key: str,
    document_paths: List[Path],
    corpus_name: str
) -> Dict:
    """
    Main function: Upload documents to Gemini File Search.

    High-level workflow:
    1. Initialize Gemini client
    2. Create File Search Store (persistent container)
    3. Upload all documents to the store
    4. Return corpus metadata (includes store name for queries)

    Args:
        gemini_api_key: Google Gemini API key
        document_paths: List of document file paths
        corpus_name: Name for the knowledge base

    Returns:
        Corpus metadata dict with:
        - file_search_store_name: Store resource name (CRITICAL for queries)
        - files_indexed: Number of files uploaded
        - storage_type: "File Search Store"
        - storage_persistence: "Indefinite (until manually deleted)"
        - created_at: ISO timestamp
        - cost_estimate: Estimated indexing cost

    Example:
        >>> docs = [Path("doc1.txt"), Path("doc2.txt")]
        >>> corpus = await upload_to_gemini("api_key", docs, "my-docs")
        >>> print(corpus['file_search_store_name'])
        fileSearchStores/abc123xyz

        # Later, user can query from ANY device with same API key:
        >>> client = genai.Client(api_key="api_key")
        >>> response = client.models.generate_content(
        ...     model='gemini-2.5-flash',
        ...     contents='Your question here',
        ...     config=types.GenerateContentConfig(
        ...         tools=[types.Tool(
        ...             file_search=types.FileSearch(
        ...                 file_search_store_names=['fileSearchStores/abc123xyz']
        ...             )
        ...         )]
        ...     )
        ... )
    """
    # Initialize Gemini client
    client = genai.Client(api_key=gemini_api_key)

    print(f"🧠 Gemini File Search Upload")
    print(f"   Corpus: {corpus_name}")
    print(f"   Documents: {len(document_paths)}")

    # Create File Search Store
    store_name = await create_file_search_store(
        client=client,
        store_name=corpus_name,
        display_name=corpus_name
    )

    # Upload documents
    uploaded_files = await upload_documents_to_store(
        client=client,
        store_name=store_name,
        document_paths=document_paths
    )

    # Calculate cost estimate
    total_size = sum(doc.stat().st_size for doc in document_paths)
    # Rough estimate: ~5 characters per token, $0.15 per 1M tokens
    estimated_tokens = total_size // 5
    cost_estimate = (estimated_tokens / 1_000_000) * 0.15

    # Build corpus metadata
    corpus_metadata = {
        'file_search_store_name': store_name,  # CRITICAL - needed for queries
        'corpus_name': corpus_name,
        'files_indexed': len(uploaded_files),
        'storage_type': 'File Search Store',
        'storage_persistence': 'Indefinite (until manually deleted)',
        'globally_accessible': True,  # Same API key from any client
        'created_at': datetime.now().isoformat(),
        'total_size_bytes': total_size,
        'estimated_tokens': estimated_tokens,
        'cost_estimate_usd': round(cost_estimate, 4),
        'uploaded_files': uploaded_files[:10]  # First 10 for reference
    }

    print(f"\n🎉 Knowledge base created successfully!")
    print(f"\n📊 Summary:")
    print(f"   Store name: {store_name}")
    print(f"   Files indexed: {len(uploaded_files)}")
    print(f"   Total size: {total_size / 1024 / 1024:.2f} MB")
    print(f"   Estimated tokens: {estimated_tokens:,}")
    print(f"   Indexing cost: ${cost_estimate:.4f}")
    print(f"\n💡 Query instructions:")
    print(f"   Use store name in your queries: {store_name}")
    print(f"   Storage: FREE (no storage fees)")
    print(f"   Queries: FREE (only pay for generation ~$0.001/query)")

    return corpus_metadata


def generate_query_guide(
    corpus_metadata: Dict,
    output_path: Path
) -> Path:
    """
    Generate a query guide showing how to use the knowledge base.

    Creates a markdown file with:
    - Python SDK example
    - AI Studio instructions
    - Mobile app instructions
    - Cost information

    Args:
        corpus_metadata: Metadata dict from upload_to_gemini
        output_path: Where to save the guide

    Returns:
        Path to created guide
    """
    store_name = corpus_metadata['file_search_store_name']
    corpus_name = corpus_metadata['corpus_name']
    files_count = corpus_metadata['files_indexed']

    guide = f"""# Query Guide: {corpus_name}

Your knowledge base has been created successfully! 🎉

## Knowledge Base Details

- **Store Name:** `{store_name}`
- **Files Indexed:** {files_count}
- **Storage:** FREE (indefinite, no storage fees)
- **Queries:** FREE (only pay for generation ~$0.001/query)

---

## 📚 Official Documentation

**Google Gemini File Search documentation:**
- https://ai.google.dev/gemini-api/docs/file-search
- https://ai.google.dev/api/file-search

⚠️ **CRITICAL:** You must use the **SAME Gemini API key** you provided to the Apify actor. File Search Stores are tied to the API key that created them.

---

## How to Query Your Knowledge Base

Google supports multiple methods for querying File Search Stores. Choose the one that fits your workflow:

### Method 1: Google AI Studio (Web Interface - Easiest)

**No coding required!**

1. Visit **https://aistudio.google.com**
2. Sign in with the **same Google account** (same API key)
3. Create a new chat
4. Click **"Add resources"** → **"File Search Stores"**
5. Select **`{corpus_name}`** from your stores list
6. Ask questions naturally - citations included automatically!

**This is the easiest method for most users.**

---

### Method 2: Python SDK (For Developers)

**Official Gemini Python SDK example:**

```python
from google import genai
from google.genai import types

# IMPORTANT: Use the SAME API key you provided to Apify actor
client = genai.Client(api_key="YOUR_GEMINI_API_KEY")

# Query your knowledge base (per Google's documentation)
response = client.models.generate_content(
    model='gemini-2.5-flash',  # or gemini-3-pro for higher quality
    contents='Your question here',
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=['{store_name}']
                )
            )
        ]
    )
)

print(response.text)

# Access citations (optional)
if response.candidates[0].grounding_metadata:
    print("\\nSources:")
    for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
        print(f"  - {{chunk.retrieved_context.title}}")
```

**Install SDK:** `pip install google-genai`

**Full SDK docs:** https://ai.google.dev/gemini-api/docs/quickstart?lang=python

---

### Method 3: Mobile Apps (iOS/Android)

**Gemini mobile apps support File Search:**

1. Download Gemini app (iOS/Android)
2. Sign in with the **same Google account**
3. Start a new chat
4. Your File Search stores are automatically available
5. Reference by name: "{corpus_name}"
6. Ask questions naturally

---

## Example Queries

Here are some example questions you can ask:

```python
queries = [
    "What are the main topics covered?",
    "Summarize the key concepts",
    "Find examples of best practices",
    "What are the common mistakes to avoid?",
    "Explain [specific concept] in simple terms",
    # Add your own questions here
]

for query in queries:
    print(f"\\nQ: {{query}}")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(file_search=types.FileSearch(
                file_search_store_names=['{store_name}']
            ))]
        )
    )
    print(f"A: {{response.text}}\\n")
```

---

## Cost Per Query

**FREE:**
- ✅ Storage (unlimited, indefinite)
- ✅ Vector search
- ✅ Retrieval

**Paid:**
- Gemini generation only: ~$0.0004-0.0008 per query
  - 100 queries: ~$0.05-0.10
  - 1,000 queries: ~$0.50-1.00

**Your knowledge base queries are essentially FREE.**

---

## Persistence

Your knowledge base is **permanent** until you delete it:

- Query today, tomorrow, next year
- No re-indexing needed (unless you scrape new data)
- No storage fees
- No search fees
- Only generation fees (~$0.001/query)

**Break-even:** After just 2-3 queries, you've saved money vs re-scraping!

---

## Next Steps

1. **Start querying** - Try the Python SDK examples above
2. **Save your API key** - Keep it secure
3. **Experiment** - Ask 10-20 diverse questions to explore your data
4. **Discover patterns** - Let AI find connections you might miss
5. **Re-scrape if needed** - Run actor again to update knowledge base

---

**Generated by:** Gemini Knowledge Scraper Actor
**Created:** {corpus_metadata['created_at']}
**Support:** Contact actor developer or check README
"""

    output_path.write_text(guide, encoding='utf-8')
    print(f"📖 Query guide created: {output_path}")

    return output_path


# ========== HELPER FUNCTIONS ==========

def list_file_search_stores(client: genai.Client) -> List[Dict]:
    """
    List all File Search Stores for this API key.

    Useful for debugging and verifying stores were created.

    Args:
        client: Initialized Gemini client

    Returns:
        List of store metadata dicts
    """
    stores = client.file_search_stores.list()
    store_list = []

    for store in stores:
        store_list.append({
            'name': store.name,
            'display_name': store.display_name,
            'created_time': store.create_time
        })

    return store_list


def delete_file_search_store(client: genai.Client, store_name: str):
    """
    Delete a File Search Store (removes all indexed data).

    WARNING: This is permanent and cannot be undone!

    Args:
        client: Initialized Gemini client
        store_name: Store resource name (e.g., "fileSearchStores/abc123")
    """
    client.file_search_stores.delete(name=store_name)
    print(f"🗑️  Deleted File Search Store: {store_name}")
