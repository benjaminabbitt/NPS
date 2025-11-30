# Amusement Parks Directory

This directory contains structured data for 50 amusement park locations with geocoded addresses and integrated coaster information.

## Directory Structure

Each park has its own directory containing:

1. **`[Park Name].md`** - Main park report with:
   - Geocoded address in format: `Address [lat, lon]`
   - Placeholder sections for park information, planning tips, and nearby attractions
   - Ready for detailed research and enhancement

2. **`user-data.md`** - Interactive checklist with:
   - Geocoded address
   - Park visited checkbox
   - Complete coaster list with:
     - Three rider checkboxes (Honor, Ben, Amber) per coaster
     - Manufacturer information
     - Notes section for each coaster
   - Park notes section for general observations

## Statistics

- **Total Parks:** 50 directories
- **Total Markdown Files:** 199 (main reports + user data files + this README)
- **Total Coasters:** 100 coasters integrated across all parks
- **All Parks Geocoded:** Yes ✓

## Notable Parks by Coaster Count

Top parks with most coasters documented:
- Cedar Point: 7 coasters
- Hersheypark: 5 coasters
- Busch Gardens Tampa: 5 coasters
- Six Flags Magic Mountain: 5 coasters
- Kings Island: 5 coasters

## Geocoding Format

All addresses use square bracket notation for coordinates to distinguish from descriptive parenthetical text:

```markdown
**Address:** 1 Cedar Point Dr, Sandusky, OH 44870 [41.4823, -82.6835]
```

## Usage

1. **Trip Planning:** Use user-data.md files to track visits and rides
2. **Research Enhancement:** Fill in placeholder sections in main report files with detailed information
3. **Family Tracking:** Three checkboxes per coaster allow tracking rides for Honor, Ben, and Amber
4. **Notes:** Document experiences, wait times, tips for each coaster

## Data Sources

- Geocoding: `/workspace/src/geocoding/geocoded_data.json`
- Coaster data: `/workspace/1-Raw Input Data/Amusement Parks/Raw Input.txt`
- Generation script: `/workspace/src/amusement_parks/generate_park_files.py`

---

**Last Updated:** 2025-11-26
**Generation Date:** 2025-11-26
