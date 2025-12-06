# Amber's Data Scripts

This directory contains two scripts for managing "Amber's Data" sections in NPS site files:

1. **add_ambers_data.py** - Adds Amber's Data from CSV spreadsheet to user-data.md files
2. **extract_ambers_data.py** - Extracts Amber's Data sections into separate ambers-data.md files

---

## Script 1: add_ambers_data.py

This script processes the CSV spreadsheet from `1-Raw Input Data/NPS/` and adds "Amber's Data" sections to all existing `user-data.md` files.

## What It Does

1. **Reads CSV Data** - Extracts visitor center information from the spreadsheet:
   - Visitor Center name
   - Full address (street, city, state, zip)
   - Operating hours (for each day of the week)

2. **Geocodes Addresses** - Looks up latitude/longitude for each address:
   - Uses Nominatim (OpenStreetMap) geocoding service
   - Caches results to `geocode_cache.json` to avoid re-geocoding
   - Respects rate limits (1.1 second delay between requests)

3. **Adds "Amber's Data" Section** - Inserts formatted data into `user-data.md`:
   - Placed before "Review / Personal Notes" section
   - Includes geocoded coordinates in parentheses after address
   - Formats hours intelligently (groups consecutive days)

4. **Verifies Visitor Centers** - Checks if visitor center is in cancellation stamps

## Output Format

The script adds a section like this to each `user-data.md`:

```markdown
## Amber's Data (from spreadsheet)

**Visitor Center:** Casa Grande Ruins National Monument

**Address:** 1100 W Ruins Dr, Coolidge, Arizona 85128 (32.995459, -111.535528)

**Hours:** Daily: 9:00 AM–4:00 PM
```

## Usage

```bash
# From workspace root
python src/add_ambers_data.py
```

## Requirements

- Python 3.8+
- httpx library for async HTTP requests

```bash
pip install httpx
```

## Geocode Cache

The script maintains a `geocode_cache.json` file to avoid re-geocoding addresses.

**Format:**
```json
{
  "1100 W Ruins Dr, Coolidge, Arizona 85128": [32.995459, -111.535528],
  "..."
}
```

## CSV Column Mapping

The script reads these columns from the spreadsheet:

| CSV Column | Purpose |
|------------|---------|
| `National Park` | Site name (used to find directory) |
| `Visitor Center Location` | Visitor center name |
| `Visitor Center Address` | Street address |
| `Visitor Center City` | City |
| `Visitor Center State` | State |
| `Visitor Center Zip` | ZIP code |
| `Sunday.1` through `Saturday.1` | Operating hours |

**Note:** The `.1` suffix is because the CSV has duplicate column names (park hours vs visitor center hours).

## Next Steps

After running this script, you should:

1. **Verify visitor centers** - Check that visitor center from CSV matches cancellation stamp locations
2. **Mark checkboxes** - Add checkmarks `[x]` to visitor centers that are primary stamp locations
3. **Update coordinates** - Add geocoded coordinates to cancellation stamp sections
4. **Review hours** - Verify hours are accurate (some may have changed since CSV was created)

## Skipped Sites

The script will skip sites where:
- Directory doesn't exist in `2-Enhanced Data/NPS/`
- `user-data.md` file doesn't exist
- No visitor center address in CSV
- "Amber's Data" section already exists

## Example Output

```
================================================================================
Adding Amber's Data from CSV Spreadsheet
================================================================================

Loading geocode cache...
✓ Loaded 15 cached geocodes

Reading CSV spreadsheet...
✓ Found 425 sites in CSV

Processing sites...
--------------------------------------------------------------------------------

Birmingham Civil Rights NM
  ✓ Added Amber's Data to Birmingham Civil Rights NM

Freedom Riders NM
  ✓ Added Amber's Data to Freedom Riders NM

...

================================================================================
SUMMARY
================================================================================
✓ Processed: 387
⚠ Skipped: 38
📍 Total geocodes in cache: 402

Geocodes saved to: geocode_cache.json
```

## Troubleshooting

**"CSV file not found"**
- Ensure CSV is at `1-Raw Input Data/NPS/Untitled spreadsheet - US Parks.csv`

**"Directory not found"**
- Site hasn't been researched yet - this is normal
- Directory name must match site name from CSV exactly

**Geocoding errors**
- Nominatim may be rate-limited - script will retry later
- Invalid addresses will be cached as `null` and skipped

**Duplicate sections**
- Script checks for existing "Amber's Data" and skips if present
- Safe to run multiple times

---

## Script 2: extract_ambers_data.py

This script extracts "Amber's Data" sections from existing user-data.md or main site files and creates separate `ambers-data.md` files.

### Purpose
- Finds "Amber's Data" sections in either user-data.md or main site report files
- Extracts the entire section content
- Removes hash values in square brackets (e.g., [ff436f], [942cba])
- Geocodes addresses that don't already have coordinates
- Creates clean `ambers-data.md` files in each site directory

### Usage
```bash
python3 src/extract_ambers_data.py
```

### Features
1. **Automatic Detection** - Searches both user-data.md and main site files
2. **Hash Removal** - Strips color hash codes like [ff436f] from content
3. **Geocoding** - Adds coordinates to addresses missing them
4. **Caching** - Uses geocode_cache.json to avoid redundant API calls
5. **Smart Processing** - Skips sites where ambers-data.md already exists

### Output Format

Creates files like this:

```markdown
# Amber's Data

**Visitor Center:** Capulin Volcano Visitor Center

**Address:** 44 Volcano Road, Capulin, New Mexico 88414 (36.7787156, -103.9803504)

**Hours:** Hours not available
```

### Processing Summary

Based on the most recent run:

- **Total NPS site directories:** 438
- **ambers-data.md files created:** 380
- **Sites without Amber's Data:** 58
- **Total addresses found:** 387
- **Addresses with geocodes:** 234 (60.5%)
- **Addresses without geocodes:** 153 (39.5%)

### Why Some Addresses Aren't Geocoded

Addresses without geocodes are typically:
- Vague or incomplete (e.g., "Highway 63, Bryce")
- Non-standard formats that couldn't be geocoded
- Already in geocode cache as unmappable (null values)

### Dependencies

- **Python 3** standard library only
- No external packages required (uses urllib instead of httpx)

### Rate Limiting

- 1.1 seconds between geocoding requests
- Uses OpenStreetMap Nominatim API
- Respects terms of service

### Example Output

```
================================================================================
Extracting Amber's Data from NPS Site Files
================================================================================

Loading geocode cache...
✓ Loaded 660 cached geocodes
✓ Found 438 site directories

Processing sites...
--------------------------------------------------------------------------------

Abraham Lincoln Birthplace NHP
  ✓ Created ambers-data.md

Acadia NP
  ✓ Created ambers-data.md

...

================================================================================
SUMMARY
================================================================================
✓ Created ambers-data.md files: 380
⊘ Already existed (skipped): 0
- No Amber's Data found: 58
✗ Errors encountered: 0
📍 Addresses geocoded in this run: 20
📍 Total geocodes in cache: 680

Geocodes saved to: geocode_cache.json
```
