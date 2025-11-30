#!/usr/bin/env python3
"""
Sync completed NPS research to Chroma vector database
"""
import chromadb
from pathlib import Path
import json
from datetime import datetime

# Sites within 500 miles of St. Louis (completed 2025-11-25)
COMPLETED_SITES = [
    # First batch (synced earlier)
    "Gateway Arch NP",
    "Ste. Geneviève NHP",
    "Lincoln Home NHS",
    "Ozark NSR",
    "Wilson's Creek NB",
    "Mammoth Cave NP",
    "Shiloh NMP",
    "Indiana Dunes NP",
    "George Washington Carver NM",
    # Second batch (newly completed)
    "Arkansas Post N MEM",
    "Fort Donelson NB",
    "Harry S Truman NHS",
    "Pea Ridge NMP",
    "Stones River NB",
    # Third batch (reformatted and completed)
    "Cuyahoga Valley NP",
    "Fort Scott NHS",
    "George Rogers Clark NHP",
    "Herbert Hoover NHS",
]

def main():
    # Initialize Chroma client
    client = chromadb.PersistentClient(path="./chroma.db")

    # Get or create collection
    collection = client.get_or_create_collection(
        name="nps_research",
        metadata={"description": "NPS site research data"}
    )

    print(f"Connected to Chroma database")
    print(f"Collection: {collection.name}")
    print(f"Current count: {collection.count()}")
    print()

    base_path = Path("2-Enhanced Data/NPS")
    added_count = 0
    updated_count = 0

    for site_name in COMPLETED_SITES:
        site_dir = base_path / site_name
        main_report = site_dir / f"{site_name}.md"
        user_data = site_dir / "user-data.md"

        if not main_report.exists():
            print(f"⚠️  Warning: {site_name} - main report not found")
            continue

        # Read the main report
        with open(main_report, 'r', encoding='utf-8') as f:
            content = f.read()

        # Create document ID
        doc_id = f"nps_{site_name.lower().replace(' ', '_')}"

        # Create metadata
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
            # Update existing document
            collection.update(
                ids=[doc_id],
                documents=[content],
                metadatas=[metadata]
            )
            updated_count += 1
            print(f"✓ Updated: {site_name}")
        else:
            # Add new document
            collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[metadata]
            )
            added_count += 1
            print(f"✓ Added: {site_name}")

    print()
    print(f"=== Sync Complete ===")
    print(f"Added: {added_count} sites")
    print(f"Updated: {updated_count} sites")
    print(f"Total in collection: {collection.count()}")

if __name__ == "__main__":
    main()
