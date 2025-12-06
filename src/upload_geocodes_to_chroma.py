#!/usr/bin/env python3
"""
Script to upload geocode data to Chroma database in batches.
This script processes the batched geocode data and uploads it to the nps_geocodes collection.
"""

import json
import subprocess
import sys

def upload_batch_to_chroma(batch_num, documents, ids, metadatas):
    """
    Upload a single batch to Chroma using the MCP CLI.
    Note: This is a placeholder - actual MCP calls need to be made through the MCP interface.
    """
    print(f"Processing batch {batch_num}...")
    print(f"  Documents: {len(documents)}")
    print(f"  IDs: {len(ids)}")
    print(f"  Metadatas: {len(metadatas)}")

    # Create batch data file
    batch_data = {
        'documents': documents,
        'ids': ids,
        'metadatas': metadatas
    }

    batch_file = f'/tmp/chroma_batch_{batch_num}.json'
    with open(batch_file, 'w') as f:
        json.dump(batch_data, f)

    print(f"  Saved to: {batch_file}")
    return batch_file

def main():
    print("="*60)
    print("Geocode Data Upload to Chroma - Batch Processor")
    print("="*60)

    upload_results = []
    total_uploaded = 0

    # Process batches 1-6 (batch 0 already uploaded)
    for batch_num in range(1, 7):
        batch_file = f'/tmp/batch_{batch_num}.json'

        try:
            with open(batch_file, 'r') as f:
                batch = json.load(f)

            output_file = upload_batch_to_chroma(
                batch_num,
                batch['documents'],
                batch['ids'],
                batch['metadatas']
            )

            upload_results.append({
                'batch': batch_num,
                'count': len(batch['documents']),
                'status': 'prepared',
                'file': output_file
            })

            total_uploaded += len(batch['documents'])

        except Exception as e:
            print(f"ERROR processing batch {batch_num}: {e}")
            upload_results.append({
                'batch': batch_num,
                'status': 'failed',
                'error': str(e)
            })

    print("\n" + "="*60)
    print("Upload Summary")
    print("="*60)
    print(f"Batch 0: 100 documents (already uploaded)")
    for result in upload_results:
        if result['status'] == 'prepared':
            print(f"Batch {result['batch']}: {result['count']} documents prepared at {result['file']}")
        else:
            print(f"Batch {result['batch']}: FAILED - {result.get('error', 'Unknown error')}")

    print(f"\nTotal documents in remaining batches: {total_uploaded}")
    print(f"Grand total (including batch 0): {total_uploaded + 100}")
    print("\nBatch files are ready for MCP upload.")

    return upload_results

if __name__ == '__main__':
    results = main()
    sys.exit(0 if all(r['status'] == 'prepared' for r in results) else 1)
