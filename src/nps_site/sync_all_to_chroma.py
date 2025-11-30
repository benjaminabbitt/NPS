#!/usr/bin/env python3
"""
Sync ALL NPS site research to Chroma vector database.
Also updates the nps_geocodes collection with new geocodes from the cache.
"""
import chromadb
from pathlib import Path
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional


def extract_geocodes_from_content(content: str) -> List[Tuple[str, float, float]]:
    """
    Extract address-geocode pairs from markdown content.
    Returns list of (address, lat, lon) tuples.
    """
    geocodes = []

    # Pattern: address (lat, lon) where lat/lon are decimals
    # Match: "123 Main St, City, ST 12345 (38.123, -90.456)"
    pattern = r'(\d+[^(]+?[A-Z]{2}\s+\d{5})\s*\((-?\d+\.\d+),\s*(-?\d+\.\d+)\)'

    for match in re.finditer(pattern, content):
        address = match.group(1).strip()
        lat = float(match.group(2))
        lon = float(match.group(3))
        geocodes.append((address, lat, lon))

    return geocodes


def sync_research_collection(client: chromadb.PersistentClient, base_path: Path) -> Dict:
    """Sync all NPS research documents to the nps_research collection."""
    collection = client.get_or_create_collection(
        name="nps_research",
        metadata={"description": "NPS site research data"}
    )

    print(f"Syncing to nps_research collection...")
    print(f"Current count: {collection.count()}")

    stats = {"added": 0, "updated": 0, "skipped": 0, "errors": []}

    # Get all site directories
    site_dirs = sorted([d for d in base_path.iterdir() if d.is_dir()])

    for site_dir in site_dirs:
        site_name = site_dir.name

        # Find main report file (may have different naming conventions)
        main_report = None
        for md_file in site_dir.glob("*.md"):
            if md_file.name not in ("user-data.md", "ambers-data.md", "CLAUDE.md"):
                main_report = md_file
                break

        if not main_report or not main_report.exists():
            stats["skipped"] += 1
            continue

        try:
            content = main_report.read_text(encoding='utf-8')

            # Create document ID (normalize site name)
            normalized = site_name.lower().replace(' ', '_').replace("'", '').replace(',', '')
            doc_id = f"nps_{normalized}"

            # Create metadata
            user_data = site_dir / "user-data.md"
            metadata = {
                "site_name": site_name,
                "type": "nps_site",
                "has_user_data": user_data.exists(),
                "synced_at": datetime.now().isoformat(),
                "file_path": str(main_report)
            }

            # Check if document already exists
            existing = collection.get(ids=[doc_id])

            if existing['ids']:
                collection.update(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[metadata]
                )
                stats["updated"] += 1
            else:
                collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[metadata]
                )
                stats["added"] += 1

        except Exception as e:
            stats["errors"].append(f"{site_name}: {e}")

    return stats


def sync_geocodes_collection(client: chromadb.PersistentClient, cache_file: Path) -> Dict:
    """Sync geocode cache to the nps_geocodes collection."""
    collection = client.get_or_create_collection(
        name="nps_geocodes",
        metadata={"description": "Geocoded addresses for NPS sites"}
    )

    print(f"\nSyncing to nps_geocodes collection...")
    print(f"Current count: {collection.count()}")

    stats = {"added": 0, "updated": 0, "skipped": 0}

    if not cache_file.exists():
        print(f"Warning: Cache file not found: {cache_file}")
        return stats

    with open(cache_file, 'r') as f:
        cache = json.load(f)

    print(f"Cache contains {len(cache)} entries")

    # Get existing IDs
    existing_results = collection.get(include=['metadatas'])
    existing_addresses = {
        meta.get('address', ''): idx
        for idx, meta in enumerate(existing_results.get('metadatas', []))
    }

    for address, coords in cache.items():
        if not coords or len(coords) != 2:
            stats["skipped"] += 1
            continue

        lat, lon = coords

        # Create document ID from address
        doc_id = f"geo_{hash(address) & 0xFFFFFFFF:08x}"

        metadata = {
            "address": address,
            "latitude": lat,
            "longitude": lon,
            "synced_at": datetime.now().isoformat()
        }

        # Create a simple document text for the address
        document = f"{address} ({lat}, {lon})"

        try:
            if address in existing_addresses:
                # Update existing
                existing_id = existing_results['ids'][existing_addresses[address]]
                collection.update(
                    ids=[existing_id],
                    documents=[document],
                    metadatas=[metadata]
                )
                stats["updated"] += 1
            else:
                # Add new
                collection.add(
                    ids=[doc_id],
                    documents=[document],
                    metadatas=[metadata]
                )
                stats["added"] += 1
        except Exception:
            # ID collision - try with a different ID
            try:
                alt_id = f"geo_{hash(address + str(lat)):08x}"
                collection.upsert(
                    ids=[alt_id],
                    documents=[document],
                    metadatas=[metadata]
                )
                stats["added"] += 1
            except Exception:
                stats["skipped"] += 1

    return stats


def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(description='Sync NPS data to Chroma')
    parser.add_argument('--research-only', action='store_true',
                        help='Only sync research collection')
    parser.add_argument('--geocodes-only', action='store_true',
                        help='Only sync geocodes collection')
    args = parser.parse_args()

    print("=" * 70)
    print("NPS Data Sync to Chroma")
    print("=" * 70)

    # Initialize Chroma client
    client = chromadb.PersistentClient(path="./chroma.db")

    base_path = Path("2-Enhanced Data/NPS")
    cache_file = Path("geocode_cache.json")

    if not base_path.exists():
        print(f"Error: Base path not found: {base_path}")
        return

    # Sync research collection
    if not args.geocodes_only:
        research_stats = sync_research_collection(client, base_path)
        print(f"\nResearch sync complete:")
        print(f"  Added: {research_stats['added']}")
        print(f"  Updated: {research_stats['updated']}")
        print(f"  Skipped: {research_stats['skipped']}")
        if research_stats['errors']:
            print(f"  Errors: {len(research_stats['errors'])}")

    # Sync geocodes collection
    if not args.research_only:
        geocode_stats = sync_geocodes_collection(client, cache_file)
        print(f"\nGeocodes sync complete:")
        print(f"  Added: {geocode_stats['added']}")
        print(f"  Updated: {geocode_stats['updated']}")
        print(f"  Skipped: {geocode_stats['skipped']}")

    # Show final counts
    print("\n" + "=" * 70)
    print("FINAL COLLECTION COUNTS")
    print("=" * 70)

    for coll_name in ["nps_research", "nps_geocodes"]:
        try:
            coll = client.get_collection(coll_name)
            print(f"  {coll_name}: {coll.count()} documents")
        except Exception:
            print(f"  {coll_name}: (not found)")

    print("\n" + "=" * 70)
    print("Sync complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
