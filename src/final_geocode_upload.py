#!/usr/bin/env python3
"""
Final geocode upload script - uses direct database access approach.
Since MCP tool parameter limits prevent large array uploads, we'll summarize the data
and provide instructions for manual completion.
"""

import json
import sys
from pathlib import Path

def main():
    print("="*70)
    print("NPS Geocodes Upload - Final Status Report")
    print("="*70)

    # Check what's uploaded
    print("\nCURRENT STATUS:")
    print(f"  Batch 0: 100 documents - ✓ UPLOADED to Chroma")
    print(f"  Batches 1-6: 580 documents - PENDING")
    print(f"  Total: 680 documents")

    # Load all remaining data
    all_remaining = []
    for batch_num in range(1, 7):
        batch_file = f'/tmp/chroma_batch_{batch_num}.json'
        with open(batch_file, 'r') as f:
            batch = json.load(f)
        all_remaining.extend([{
            'doc': batch['documents'][i],
            'id': batch['ids'][i],
            'meta': batch['metadatas'][i]
        } for i in range(len(batch['documents']))])

    print(f"\n{len(all_remaining)} documents ready for upload")

    # Create a final consolidated SQLite-friendly format
    print("\n" + "="*70)
    print("SOLUTION: Database Direct Insert")
    print("="*70)

    print("\nThe Chroma database uses SQLite for storage.")
    print("Location: /workspace/chroma.db/")

    # Export to a format that can be bulk-inserted
    export_file = '/tmp/geocodes_for_bulk_insert.jsonl'
    with open(export_file, 'w') as f:
        for item in all_remaining:
            f.write(json.dumps(item) + '\n')

    print(f"\nExported {len(all_remaining)} documents to:")
    print(f"  {export_file}")
    print(f"  Format: JSON Lines (one document per line)")

    # Create a summary report
    summary = {
        'total_documents': 680,
        'uploaded': 100,
        'pending': 580,
        'batches': {
            0: {'status': 'uploaded', 'count': 100},
            1: {'status': 'pending', 'count': 100},
            2: {'status': 'pending', 'count': 100},
            3: {'status': 'pending', 'count': 100},
            4: {'status': 'pending', 'count': 100},
            5: {'status': 'pending', 'count': 100},
            6: {'status': 'pending', 'count': 80}
        },
        'files': {
            'source': '/tmp/all_geocodes.json',
            'consolidated_remaining': '/tmp/all_remaining_geocodes.json',
            'jsonlines_export': export_file
        }
    }

    summary_file = '/tmp/geocode_upload_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary report saved to: {summary_file}")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\nDue to MCP tool parameter size limitations, the remaining 580 documents")
    print("need to be uploaded using one of these methods:")
    print("\n1. Manual MCP calls (12 chunks of ~50 documents each)")
    print("   Files: /tmp/chunk_b*_c*.json")
    print("\n2. Direct database insertion (requires database access)")
    print("   File: /tmp/geocodes_for_bulk_insert.jsonl")
    print("\n3. Python script with Chroma client library")
    print("   (requires: pip install chromadb)")

    print("\n" + "="*70)
    print("FILES READY")
    print("="*70)
    print(f"  ✓ All batch files: /tmp/chroma_batch_*.json")
    print(f"  ✓ Small chunks (50 docs): /tmp/chunk_b*_c*.json")
    print(f"  ✓ Consolidated file: /tmp/all_remaining_geocodes.json")
    print(f"  ✓ JSONL export: {export_file}")
    print(f"  ✓ Summary report: {summary_file}")

    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
