# Content Storage

## Overview

PaperTracker provides an optional **content storage** feature that persists full paper metadata to a SQLite database. This is separate from the deduplication feature and enables advanced use cases such as:

- Building a local paper library with complete metadata
- Adding LLM-enhanced fields (e.g., translations, summaries)
- Querying historical paper collections
- Analyzing paper trends over time

When enabled, every paper fetched from arXiv is stored with complete metadata including title, authors, abstract, categories, URLs, and timestamps.

## Configuration

Content storage is controlled by the `state.content_storage_enabled` option in your YAML configuration file.

### Basic Setup

```yaml
state:
  enabled: true                        # Must be enabled for content storage
  db_path: null                        # Use default database/papers.db
  content_storage_enabled: true        # Enable content storage (default: false)
```

### Configuration Parameters

- **`state.enabled`** (boolean, required): Must be `true` to enable content storage
  - Content storage depends on the deduplication feature (seen_papers table)

- **`state.content_storage_enabled`** (boolean, default: `false`): Enable/disable full content storage
  - `true`: Save complete paper metadata to `paper_content` table
  - `false`: Only track seen papers for deduplication (no full content)

- **`state.db_path`** (string, default: `database/papers.db`): Database file path
  - Shared by both deduplication and content storage
  - Absolute path or project-relative path
  - If `null`, defaults to `database/papers.db`

## How It Works

### Storage Flow

1. **Search Execution**: Papers are fetched from arXiv based on your queries
2. **Deduplication**: New papers are identified (papers not in `seen_papers`)
3. **Mark as Seen**: All fetched papers are inserted/updated in `seen_papers` table
4. **Content Storage**: If `content_storage_enabled=true`, full metadata is saved to `paper_content` table

### Database Schema

The system uses two related tables:

#### `seen_papers` Table (Deduplication)

Tracks which papers have been seen before:

- `id`: Primary key
- `source`: Data source identifier (e.g., "arxiv")
- `source_id`: Unique ID within the source (e.g., "2601.21922")
- `doi`: Digital Object Identifier (optional)
- `doi_norm`: Normalized DOI for cross-source matching
- `title`: Paper title
- `first_seen_at`: Unix timestamp when first encountered

#### `paper_content` Table (Full Content)

Stores complete paper metadata:

- `id`: Primary key
- `seen_paper_id`: Foreign key to `seen_papers.id`
- `source`: Data source identifier
- `source_id`: Unique paper ID
- `title`: Paper title
- `authors`: JSON array of author names
- `summary`: Abstract/summary text
- `published_at`: Publication timestamp
- `updated_at`: Last update timestamp
- `fetched_at`: When this record was created
- `primary_category`: Primary arXiv category
- `categories`: JSON array of all categories
- `abstract_url`: Link to abstract page
- `pdf_url`: Link to PDF file
- `code_urls`: JSON array of code repository URLs (extracted from extra)
- `project_urls`: JSON array of project page URLs (extracted from extra)
- `doi`: Digital Object Identifier
- `translation`: Translated summary text (for future LLM enhancement)
- `language`: Target language code (e.g., "zh", "en")
- `extra`: JSON object with additional metadata

**Key Design Decisions:**

- Papers are linked via `seen_paper_id` foreign key to ensure referential integrity
- Papers not in `seen_papers` will be skipped with a warning
- The `fetched_at` timestamp allows tracking when papers were retrieved
- JSON fields enable flexible storage of arrays and nested data
- Indexes on `seen_paper_id`, `source_id`, `fetched_at`, and `primary_category` for efficient queries

## Usage Examples

### Example 1: Enable Content Storage

Configuration file (`config/papers.yml`):

```yaml
log:
  level: INFO
  to_file: true
  dir: log

state:
  enabled: true
  db_path: database/papers.db
  content_storage_enabled: true  # Enable full content storage

queries:
  - NAME: neural_compression
    OR:
      - Neural Image Compression
      - Learned Video Compression

search:
  max_results: 10
  sort_by: submittedDate
  sort_order: descending

output:
  format: text
```

Run the search:

```bash
paper-tracker --config config/papers.yml search
```

Output:

```
State management enabled: database/papers.db
Content storage enabled: database/papers.db
Fetched 10 papers
New papers: 10 (filtered 0 duplicates)
[Paper details...]
```

### Example 2: Query Stored Content

The `PaperContentStore` class provides methods to query stored papers (for future CLI commands or scripts):

```python
from pathlib import Path
from PaperTracker.storage.db import DatabaseManager
from PaperTracker.storage.content import PaperContentStore

# Initialize database connection
db_manager = DatabaseManager(Path("database/papers.db"))
content_store = PaperContentStore(db_manager)

# Get 50 most recent papers
recent_papers = content_store.get_recent_papers(limit=50)

for paper in recent_papers:
    print(f"{paper['title']} - {paper['primary_category']}")
    print(f"Authors: {', '.join(paper['authors'])}")
    print(f"PDF: {paper['pdf_url']}\n")

# Get papers from last 7 days
week_papers = content_store.get_recent_papers(limit=100, days=7)

# Get statistics
stats = content_store.get_statistics()
print(f"Total records: {stats['total_records']}")
print(f"Unique papers: {stats['unique_papers']}")
print(f"Categories: {stats['categories']}")
```

### Example 3: Add Translations (Future Enhancement)

The schema includes `translation` and `language` fields for LLM-enhanced content:

```python
# Update translation for a paper
content_store.update_translation(
    source_id="2601.21922",
    translation="这是一篇关于神经网络图像压缩的论文...",
    language="zh"
)
```

## Implementation Details

### Module Structure

- **`storage/db.py`**: Database initialization, schema definition, and `DatabaseManager` singleton
- **`storage/deduplicate.py`**: `SqliteDeduplicateStore` for tracking seen papers
- **`storage/content.py`**: `PaperContentStore` for full paper metadata storage
- **`storage/__init__.py`**: Module exports

### Key Classes

#### `DatabaseManager`

Manages the shared SQLite connection using the singleton pattern:

- Ensures only one connection per database path
- Prevents connection resource waste and concurrent write conflicts
- Supports context manager protocol for automatic cleanup
- Initializes schema on first use

#### `PaperContentStore`

Handles full paper content storage:

- `save_papers(papers)`: Save full metadata for a list of papers
- `update_translation(source_id, translation, language)`: Add translated content
- `get_recent_papers(limit, days)`: Query recent papers with optional time filter
- `get_statistics()`: Get database statistics (total records, unique papers, categories, etc.)

### Integration Points

1. **Configuration**: `AppConfig` dataclass in `config.py` includes `content_storage_enabled` flag
2. **CLI**: `cli.py` initializes `DatabaseManager` and `PaperContentStore` when enabled
3. **Database**: Schema automatically created by `init_schema()` in `db.py`
4. **Deduplication**: Content storage depends on `seen_papers` table for foreign key relationships

## Relationship with Deduplication

Content storage and deduplication are **complementary features**:

| Feature | Purpose | Table | Required |
|---------|---------|-------|----------|
| Deduplication | Track seen papers to filter duplicates | `seen_papers` | For content storage |
| Content Storage | Persist full paper metadata | `paper_content` | Optional enhancement |

**Dependency**: Content storage requires deduplication to be enabled (`state.enabled: true`) because:
- `paper_content` has a foreign key to `seen_papers`
- Papers must be marked as seen before content can be saved
- This ensures referential integrity

**Workflow**:
1. Papers are fetched from arXiv
2. Deduplication identifies new papers
3. All papers are inserted into `seen_papers` (with UPSERT)
4. If content storage is enabled, full metadata is saved to `paper_content`

## Advantages

### For Users

- **Local Library**: Build a searchable collection of papers without relying on external services
- **Offline Access**: Query paper metadata without internet connection
- **Custom Analysis**: Analyze trends, track research areas, identify patterns
- **LLM Integration**: Add translations, summaries, or other AI-enhanced content

### For Developers

- **Separation of Concerns**: Deduplication and content storage use separate tables
- **Extensible Schema**: JSON fields allow flexible metadata without schema migrations
- **Efficient Queries**: Indexes on common query patterns (time, category, source_id)
- **Transaction Safety**: Single connection prevents concurrent write conflicts

## Limitations

- **Single Process**: Database does not support concurrent writes from multiple processes
  - Use different `db_path` values for parallel runs
- **Storage Growth**: Full content storage increases database size
  - Consider periodic cleanup or archival for long-running deployments
- **No Incremental Updates**: Papers are stored as-is when fetched
  - Re-fetching the same paper creates a duplicate entry (same source_id, different fetched_at)
- **Foreign Key Constraint**: Papers not in `seen_papers` cannot be stored
  - This should not happen in normal operation, but warns if it does

## Troubleshooting

### Content Not Saved

**Problem**: Papers appear in output but not in `paper_content` table

**Solutions**:
1. Verify `state.content_storage_enabled: true` in config
2. Check that `state.enabled: true` (required for content storage)
3. Look for warnings: `Paper X not in seen_papers, skipping content save`
4. Ensure database path is writable

### Database Locked

**Problem**: Error `database is locked`

**Solution**: Ensure no other PaperTracker processes are using the same database file

```bash
# Check for running processes
ps aux | grep paper-tracker

# Kill conflicting processes
pkill -f paper-tracker
```

### Missing Fields

**Problem**: Some metadata fields are `null` in database

**Explanation**: Not all papers have all fields (e.g., DOI, code URLs)
- This is expected behavior
- JSON fields default to empty arrays: `[]`
- Scalar fields may be `null` if not available

### Reset Database

To start fresh and re-populate the database:

```bash
rm database/papers.db
paper-tracker --config config/papers.yml search
```

## Future Enhancements

The content storage feature is designed to support:

1. **Translation Service**: Automatically translate abstracts using LLMs
2. **Paper Recommendations**: Analyze stored papers to suggest related work
3. **Export Features**: Export to BibTeX, Markdown, or other formats
4. **Web Interface**: Browse and search stored papers via web UI
5. **Duplicate Detection**: Cross-source duplicate detection using DOI normalization

These features can be built on top of the existing `paper_content` table without schema changes.

## See Also

- [Storage and Deduplication](../storage.md) - For deduplication-only usage
- [Configuration Guide](../configuration.md) - For general configuration options
- [Testing Guide](testing.md) - For testing storage features
