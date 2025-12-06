# MCP Integration Package

This package provides utilities for interacting with Chroma vector database via MCP (Model Context Protocol) tools.

## Overview

The package standardizes how NPS site data is stored in and retrieved from Chroma, ensuring consistent document IDs and metadata across all sync operations.

## Collection Schema

### `nps_sites` Collection

Single unified collection containing all NPS site research data.

**Document Structure:**
```
ID: nps_<normalized_site_name>  (e.g., "nps_fort_scott_nhs")
Document: Full markdown content from [Site Name].md
Metadata:
  - site_name: str (original name, e.g., "Fort Scott NHS")
  - site_name_normalized: str (indexed, e.g., "fort_scott_nhs")
  - visited: bool (indexed, from user-data.md)
  - lat: float (visitor center latitude)
  - lon: float (visitor center longitude)
  - stamps_collected: int (count from user-data.md)
  - has_user_data: bool
  - file_path: str
  - content_hash: str (SHA256 for change detection)
  - synced_at: str (ISO timestamp)
```

### Indexed Fields

The following metadata fields are optimized for filtering:

| Field | Type | Purpose |
|-------|------|---------|
| `site_name_normalized` | string | Fast lookup by site name |
| `visited` | boolean | Filter visited/unvisited sites |

## Usage

### Normalizing Site Names

```python
from src.mcp import normalize_site_name

# Convert site name to document ID
doc_id = normalize_site_name("Fort Scott NHS")
# Returns: "nps_fort_scott_nhs"

# Handles special characters
doc_id = normalize_site_name("César E. Chávez National Monument")
# Returns: "nps_cesar_e_chavez_national_monument"

# Handles apostrophes
doc_id = normalize_site_name("Perry's Victory & International Peace MEM")
# Returns: "nps_perrys_victory_international_peace_mem"
```

### Query Filters

```python
from src.mcp.collections import QueryFilters

# Find unvisited sites
filter = QueryFilters.unvisited()
# Returns: {"visited": {"$eq": False}}

# Find sites with coordinates
filter = QueryFilters.has_coordinates()
```

**Note:** Chroma does not support geospatial proximity queries. For "sites within X miles" queries, use the routing module (`src/routing/`) which handles distance calculations.

### Collection Configuration

```python
from src.mcp.collections import DEFAULT_CONFIG, NPS_SITES_COLLECTION

# Collection name
print(NPS_SITES_COLLECTION)  # "nps_sites"

# Get metadata for collection creation
metadata = DEFAULT_CONFIG.metadata
```

## Normalization Rules

The `normalize_site_name()` function applies these transformations in order:

1. **Remove apostrophes** - Both straight (`'`) and curly (`'`, `'`) variants
2. **Unicode normalize** - NFKD normalization, strip combining characters (é → e)
3. **Lowercase** - Convert to lowercase
4. **Replace special chars** - Any non-alphanumeric becomes underscore
5. **Collapse underscores** - Multiple underscores become single
6. **Strip edges** - Remove leading/trailing underscores
7. **Add prefix** - Prepend `nps_`

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports |
| `normalize.py` | Site name normalization functions |
| `collections.py` | Collection schemas and query helpers |
| `test_normalize.py` | Unit tests for normalization |

## Integration with MCP Tools

This package is designed to work with Chroma MCP tools:

```python
# Example: Adding a document via MCP
from src.mcp import normalize_site_name
from src.mcp.collections import NPS_SITES_COLLECTION

doc_id = normalize_site_name("Fort Scott NHS")
# Use with mcp__chroma__chroma_add_documents tool
```

See `CLAUDE.md` for AI assistant integration guidelines.
