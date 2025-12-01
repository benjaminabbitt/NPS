#!/usr/bin/env python3
"""
Geocode NPS sites and add YAML frontmatter with coordinates
"""
import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


def extract_from_ambers_data(content: str) -> Optional[Tuple[str, Optional[Tuple[float, float]]]]:
    """
    Extract address and geocode from Amber's Data section in user-data.md
    Returns (address, geocode) where geocode is (lat, lon) if found, None otherwise
    """
    # Look for Amber's Data section
    if "## Amber's Data" not in content:
        return None

    # Extract address line: **Address:** [address] ([lat], [lon])
    address_pattern = r'\*\*Address:\*\*\s+([^\n]+)'
    match = re.search(address_pattern, content)
    if not match:
        return None

    address_line = match.group(1).strip()

    # Check if geocode is in the address
    geocode_pattern = r'\(([0-9.-]+),\s*([0-9.-]+)\)'
    geocode_match = re.search(geocode_pattern, address_line)

    if geocode_match:
        lat = float(geocode_match.group(1))
        lon = float(geocode_match.group(2))
        address = re.sub(geocode_pattern, '', address_line).strip()
        return (address, (lat, lon))
    else:
        return (address_line, None)


def extract_visitor_center_info(content: str) -> Optional[Tuple[str, Optional[Tuple[float, float]]]]:
    """
    Extract visitor center address and geocode from site markdown content
    Returns (address, geocode) where geocode is (lat, lon) if found in text, None otherwise
    """
    # Look for pattern: (Address, City, State Zip (lat, lon); hours...)
    # or: (Address, City, State Zip; hours...)
    pattern = r'\*\*.*?Visitor Center\*\* \(([^;]+);'
    match = re.search(pattern, content)
    if not match:
        return None

    address_part = match.group(1).strip()

    # Check if geocode is already in the address
    geocode_pattern = r'\(([0-9.-]+),\s*([0-9.-]+)\)'
    geocode_match = re.search(geocode_pattern, address_part)

    if geocode_match:
        # Extract geocode and clean address
        lat = float(geocode_match.group(1))
        lon = float(geocode_match.group(2))
        address = re.sub(geocode_pattern, '', address_part).strip()
        return (address, (lat, lon))
    else:
        return (address_part, None)


def get_chroma_collection():
    """Get or create the nps_geocodes collection in Chroma"""
    if not CHROMA_AVAILABLE:
        return None

    try:
        client = chromadb.PersistentClient(path="chroma.db")
        collection = client.get_or_create_collection(name="nps_geocodes")
        return collection
    except Exception as e:
        print(f"  Warning: Chroma not available: {e}")
        return None


def get_geocode_from_chroma(address: str, collection) -> Optional[Tuple[float, float]]:
    """Query Chroma for cached geocode"""
    if not collection:
        return None

    try:
        results = collection.query(
            query_texts=[address],
            n_results=1
        )

        if results['ids'] and len(results['ids'][0]) > 0:
            metadata = results['metadatas'][0][0]
            if 'lat' in metadata and 'lon' in metadata:
                return (float(metadata['lat']), float(metadata['lon']))
    except Exception as e:
        print(f"  Warning: Error querying Chroma: {e}")

    return None


def store_geocode_in_chroma(address: str, geocode: Tuple[float, float], collection):
    """Store geocode in Chroma for future use"""
    if not collection:
        return

    try:
        collection.add(
            ids=[f"geocode_{hash(address)}"],
            documents=[address],
            metadatas=[{"lat": geocode[0], "lon": geocode[1], "address": address}]
        )
    except Exception as e:
        print(f"  Warning: Error storing to Chroma: {e}")


def geocode_address(address: str, collection=None) -> Optional[Tuple[float, float]]:
    """
    Geocode an address - first check Chroma cache, then use OpenStreetMap Nominatim API
    Returns (latitude, longitude) or None
    """
    # First, check Chroma cache
    if collection:
        cached = get_geocode_from_chroma(address, collection)
        if cached:
            print(f"  (from cache)")
            return cached

    # If not in cache, query OpenStreetMap
    base_url = "https://nominatim.openstreetmap.org/search"
    params = urllib.parse.urlencode({
        'q': address,
        'format': 'json',
        'limit': 1,
        'countrycodes': 'us',  # Restrict to USA
    })
    url = f"{base_url}?{params}"

    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'NPS-Research-Tool/1.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            results = json.loads(response.read().decode())

        if results:
            lat = float(results[0]['lat'])
            lon = float(results[0]['lon'])
            geocode = (lat, lon)

            # Cache the result
            if collection:
                store_geocode_in_chroma(address, geocode, collection)

            return geocode
        return None
    except Exception as e:
        print(f"  Error geocoding {address}: {e}")
        return None


def add_yaml_frontmatter(file_path: Path, geocode: Tuple[float, float]) -> bool:
    """Add or update YAML frontmatter with geocode data"""
    content = file_path.read_text()

    # Check if YAML frontmatter already exists
    if content.startswith('---\n'):
        # Update existing frontmatter
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            yaml_content = parts[1]
            rest = parts[2]

            # Update or add geocode
            if 'geocode:' in yaml_content:
                # Replace existing geocode
                yaml_content = re.sub(
                    r'geocode:.*?\n(?=\w|\n)',
                    f'geocode:\n  visitor_center: [{geocode[0]}, {geocode[1]}]\n',
                    yaml_content,
                    flags=re.DOTALL
                )
            else:
                # Add geocode to existing frontmatter
                yaml_content += f'geocode:\n  visitor_center: [{geocode[0]}, {geocode[1]}]\n'

            new_content = f'---\n{yaml_content}---\n{rest}'
        else:
            return False
    else:
        # Add new frontmatter
        yaml_frontmatter = f"""---
geocode:
  visitor_center: [{geocode[0]}, {geocode[1]}]
---

"""
        new_content = yaml_frontmatter + content

    file_path.write_text(new_content)
    return True


def geocode_site(site_path: Path, collection=None) -> bool:
    """Process a single site file"""
    print(f"\nProcessing: {site_path.parent.name}")

    content = site_path.read_text()

    # Check if already has YAML frontmatter with geocode
    if content.startswith('---\n') and 'geocode:' in content.split('---\n', 2)[1]:
        print(f"  ✓ Already has geocode in YAML")
        return True

    # First, try to extract from user-data.md if it exists
    user_data_path = site_path.parent / "user-data.md"
    info = None

    if user_data_path.exists():
        user_data_content = user_data_path.read_text()
        info = extract_from_ambers_data(user_data_content)
        if info:
            print(f"  Found in Amber's Data")

    # If not found in user-data.md, try main file
    if not info:
        info = extract_visitor_center_info(content)

    if not info:
        print(f"  ⚠ Could not extract address")
        return False

    address, existing_geocode = info
    print(f"  Address: {address}")

    # Use existing geocode or fetch new one
    if existing_geocode:
        geocode = existing_geocode
        print(f"  Geocode: [{geocode[0]}, {geocode[1]}]")
        # Store in cache for future use
        if collection:
            store_geocode_in_chroma(address, geocode, collection)
    else:
        geocode = geocode_address(address, collection)
        if not geocode:
            print(f"  ✗ Geocoding failed")
            return False
        print(f"  Geocode: [{geocode[0]}, {geocode[1]}]")

    # Add to file
    if add_yaml_frontmatter(site_path, geocode):
        print(f"  ✓ Updated file")
        return True
    else:
        print(f"  ✗ Failed to update file")
        return False


def main():
    """Geocode all NPS site files"""
    nps_dir = Path("/workspace/2-Enhanced Data/NPS")

    # Initialize Chroma collection
    print("Initializing Chroma vector database...")
    collection = get_chroma_collection()
    if collection:
        print("✓ Chroma connected")
    else:
        print("⚠ Chroma not available - will not cache geocodes")

    # Find all site markdown files (not user-data.md)
    site_files = []
    for site_dir in nps_dir.iterdir():
        if site_dir.is_dir():
            for md_file in site_dir.glob("*.md"):
                if md_file.name != "user-data.md" and md_file.name != "CLAUDE.md":
                    site_files.append(md_file)

    print(f"\nFound {len(site_files)} site files to process")

    success_count = 0
    failed = []

    for site_file in sorted(site_files):
        try:
            if geocode_site(site_file, collection):
                success_count += 1
            else:
                failed.append(site_file.parent.name)

            # Rate limit: be nice to Nominatim
            time.sleep(1.5)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed.append(site_file.parent.name)

    print(f"\n{'='*60}")
    print(f"Processed: {len(site_files)} sites")
    print(f"Success: {success_count}")
    print(f"Failed: {len(failed)}")
    if failed:
        print(f"\nFailed sites:")
        for site in failed:
            print(f"  - {site}")


if __name__ == '__main__':
    main()
