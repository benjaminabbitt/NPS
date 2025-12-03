# MCP Package - Claude Integration Guide

## Purpose

This package standardizes Chroma document IDs and metadata for NPS site data. **Always use these utilities when interacting with Chroma.**

## Critical Rules

### 1. Always Normalize Site Names

```python
from src.mcp import normalize_site_name

# CORRECT
doc_id = normalize_site_name("Fort Scott NHS")  # "nps_fort_scott_nhs"

# WRONG - never construct IDs manually
doc_id = "nps_fort_scott_nhs"  # May not match normalization rules
doc_id = f"nps_{site_name.lower().replace(' ', '_')}"  # Missing full normalization
```

### 2. Use the Unified Collection

```python
from src.mcp.collections import NPS_SITES_COLLECTION

# Collection name: "nps_sites"
# Do NOT use "nps_geocodes" or "nps_research" - these are deprecated
```

### 3. Required Metadata Fields

When adding/updating documents, always include:

```python
metadata = {
    "site_name": "Fort Scott NHS",  # Original name
    "site_name_normalized": "fort_scott_nhs",  # Without nps_ prefix
    "visited": False,  # From user-data.md checkbox
    # ... other fields as available
}
```

### 4. Indexed Fields for Filtering

Use these metadata fields in `where` clauses for efficient queries:

| Field | Use Case |
|-------|----------|
| `site_name_normalized` | Lookup by name |
| `visited` | Filter trip planning candidates |

### 5. Query Patterns

```python
from src.mcp.collections import QueryFilters

# Find unvisited sites
mcp__chroma__chroma_query_documents(
    collection_name="nps_sites",
    query_texts=["civil war battlefield"],
    where=QueryFilters.unvisited()
)

# Find by name
mcp__chroma__chroma_get_documents(
    collection_name="nps_sites",
    where=QueryFilters.by_normalized_name("fort_scott_nhs")
)

# Find sites with coordinates
mcp__chroma__chroma_get_documents(
    collection_name="nps_sites",
    where=QueryFilters.has_coordinates()
)
```

**Note:** Chroma does not support geospatial proximity queries (e.g., "within 50 miles"). For distance-based filtering, use the routing module (`src/routing/`).

## Sync Workflow

When syncing site data to Chroma:

1. Scan `2-Enhanced Data/NPS/` for site directories
2. For each site:
   - Generate ID: `normalize_site_name(site_name)`
   - Read `[Site Name].md` for document content
   - Parse `user-data.md` for `visited` status and `stamps_collected`
   - Compute `content_hash` for change detection
3. Use `mcp__chroma__chroma_add_documents` or `mcp__chroma__chroma_update_documents`

## Migration Notes

The old collections (`nps_geocodes`, `nps_research`) are being consolidated into `nps_sites`:
- Geocode data now lives in document metadata (`lat`, `lon`)
- Research content is the document body
- User tracking (`visited`, `stamps_collected`) is in metadata

## Testing

Run tests before making changes:

```bash
uv run python -m pytest src/mcp/test_normalize.py -v
```
