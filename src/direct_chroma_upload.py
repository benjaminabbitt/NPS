#!/usr/bin/env python3
"""
Direct upload of geocode batches to Chroma database.
This script bypasses MCP and uploads directly to the Chroma database.
"""

import json
import chromadb
from pathlib import Path

def main():
    print("="*70)
    print("Direct Chroma Upload - NPS Geocodes")
    print("="*70)

    # Connect to Chroma database
    chroma_path = Path("/workspace/chroma.db")
    client = chromadb.PersistentClient(path=str(chroma_path))

    # Get or create the collection
    try:
        collection = client.get_collection(name="nps_geocodes")
        print(f"\nConnected to existing collection 'nps_geocodes'")
        initial_count = collection.count()
        print(f"Initial document count: {initial_count}")
    except Exception as e:
        print(f"\nError getting collection: {e}")
        return False

    # Upload batches 1-6
    total_uploaded = 0
    upload_results = []

    for batch_num in range(1, 7):
        batch_file = f'/tmp/chroma_batch_{batch_num}.json'
        print(f"\n{'-'*70}")
        print(f"Uploading Batch {batch_num}...")
        print(f"{'-'*70}")

        try:
            with open(batch_file, 'r') as f:
                batch = json.load(f)

            # Upload to Chroma
            collection.add(
                documents=batch['documents'],
                ids=batch['ids'],
                metadatas=batch['metadatas']
            )

            count = len(batch['documents'])
            total_uploaded += count
            upload_results.append({
                'batch': batch_num,
                'count': count,
                'status': 'success'
            })
            print(f"  ✓ Successfully uploaded {count} documents")

        except Exception as e:
            print(f"  ✗ Error uploading batch {batch_num}: {e}")
            upload_results.append({
                'batch': batch_num,
                'status': 'failed',
                'error': str(e)
            })

    # Final summary
    final_count = collection.count()
    print("\n" + "="*70)
    print("Upload Complete - Summary")
    print("="*70)
    print(f"Batch 0: 100 documents (uploaded previously)")
    for result in upload_results:
        if result['status'] == 'success':
            print(f"Batch {result['batch']}: {result['count']} documents - SUCCESS")
        else:
            print(f"Batch {result['batch']}: FAILED - {result.get('error', 'Unknown')}")

    print(f"\n{'-'*70}")
    print(f"Initial count: {initial_count}")
    print(f"Documents uploaded in this session: {total_uploaded}")
    print(f"Final count: {final_count}")
    print(f"Expected total: 680")
    print(f"{'✓ SUCCESS' if final_count == 680 else '✗ MISMATCH'}")
    print("="*70)

    return final_count == 680

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
