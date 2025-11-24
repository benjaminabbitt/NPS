#!/usr/bin/env python3
"""
Direct upload of remaining geocode batches to Chroma database.
Uses chromadb Python client to directly insert the data.
"""

import json
import chromadb
from pathlib import Path

def main():
    print("="*70)
    print("Direct Chroma Upload - Remaining Batches (1-6)")
    print("="*70)

    # Connect to the Chroma database
    chroma_path = Path("/workspace/chroma.db")
    print(f"\nConnecting to Chroma database at: {chroma_path}")

    try:
        client = chromadb.PersistentClient(path=str(chroma_path))
        print("✓ Connected to Chroma")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False

    # Get the collection
    try:
        collection = client.get_collection(name="nps_geocodes")
        initial_count = collection.count()
        print(f"✓ Got collection 'nps_geocodes'")
        print(f"  Initial document count: {initial_count}")
    except Exception as e:
        print(f"✗ Failed to get collection: {e}")
        return False

    # Upload batches 1-6
    print("\n" + "="*70)
    print("Uploading Batches")
    print("="*70)

    total_uploaded = 0
    failed_batches = []

    for batch_num in range(1, 7):
        batch_file = f'/tmp/chroma_batch_{batch_num}.json'
        print(f"\nBatch {batch_num}:")
        print(f"  Loading from: {batch_file}")

        try:
            with open(batch_file, 'r') as f:
                batch = json.load(f)

            doc_count = len(batch['documents'])
            print(f"  Documents to upload: {doc_count}")

            # Add to collection
            collection.add(
                documents=batch['documents'],
                ids=batch['ids'],
                metadatas=batch['metadatas']
            )

            total_uploaded += doc_count
            print(f"  ✓ Successfully uploaded {doc_count} documents")

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed_batches.append(batch_num)

    # Final verification
    print("\n" + "="*70)
    print("Upload Complete - Verification")
    print("="*70)

    final_count = collection.count()
    expected_count = 680

    print(f"\nInitial count: {initial_count}")
    print(f"Documents uploaded: {total_uploaded}")
    print(f"Final count: {final_count}")
    print(f"Expected count: {expected_count}")

    if failed_batches:
        print(f"\n✗ Failed batches: {failed_batches}")

    if final_count == expected_count:
        print(f"\n{'='*70}")
        print("✓ SUCCESS - All 680 geocodes uploaded to Chroma!")
        print(f"{'='*70}")
        return True
    else:
        print(f"\n{'='*70}")
        print(f"✗ INCOMPLETE - Expected {expected_count}, got {final_count}")
        print(f"{'='*70}")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
