#!/usr/bin/env python3
"""
Bulk upload remaining geocode batches to Chroma.
This script reads pre-prepared batch files and outputs instructions for manual MCP upload.
"""

import json
import sys
from pathlib import Path

def main():
    print("="*70)
    print("NPS Geocodes - Bulk Upload Instructions")
    print("="*70)

    # Load all batches
    batches = []
    for batch_num in range(1, 7):
        batch_file = f'/tmp/chroma_batch_{batch_num}.json'
        with open(batch_file, 'r') as f:
            batch = json.load(f)
        batches.append({
            'num': batch_num,
            'data': batch,
            'count': len(batch['documents'])
        })

    print(f"\nLoaded {len(batches)} batches ({sum(b['count'] for b in batches)} total documents)")
    print("\nBatch Summary:")
    for b in batches:
        print(f"  Batch {b['num']}: {b['count']} documents")

    print("\n" + "="*70)
    print("UPLOAD INSTRUCTIONS")
    print("="*70)
    print("\nTo complete the upload, you need to make MCP tool calls for each batch.")
    print("Each call should use: mcp__chroma__chroma_add_documents")
    print("\nParameters for each call:")
    print("  - collection_name: 'nps_geocodes'")
    print("  - documents: array from batch file")
    print("  - ids: array from batch file")
    print("  - metadatas: array from batch file")

    print("\nBatch files are located at:")
    for b in batches:
        print(f"  Batch {b['num']}: /tmp/chroma_batch_{b['num']}.json")

    print("\n" + "="*70)
    print("ALTERNATIVE: Consolidated Upload File")
    print("="*70)

    # Create a single consolidated file with all remaining batches
    all_docs = []
    all_ids = []
    all_metas = []

    for b in batches:
        all_docs.extend(b['data']['documents'])
        all_ids.extend(b['data']['ids'])
        all_metas.extend(b['data']['metadatas'])

    consolidated = {
        'documents': all_docs,
        'ids': all_ids,
        'metadatas': all_metas
    }

    consol_file = '/tmp/all_remaining_geocodes.json'
    with open(consol_file, 'w') as f:
        json.dump(consolidated, f)

    print(f"\nAll {len(all_docs)} remaining documents consolidated into:")
    print(f"  {consol_file}")
    print(f"\nThis file contains:")
    print(f"  Documents: {len(all_docs)}")
    print(f"  IDs: {len(all_ids)}")
    print(f"  Metadatas: {len(all_metas)}")

    # Create individual batch upload scripts
    print("\n" + "="*70)
    print("Creating individual upload data files...")
    print("="*70)

    for b in batches:
        # Save a compact version for easier inspection
        summary_file = f'/tmp/batch_{b["num"]}_summary.txt'
        with open(summary_file, 'w') as f:
            f.write(f"Batch {b['num']} Summary\n")
            f.write(f"{'='*50}\n")
            f.write(f"Document count: {b['count']}\n")
            f.write(f"First 5 documents:\n")
            for i in range(min(5, b['count'])):
                f.write(f"  {i+1}. {b['data']['documents'][i]}\n")
        print(f"  Created summary: {summary_file}")

    print("\n" + "="*70)
    print("READY FOR UPLOAD")
    print("="*70)
    print(f"\nCurrent status:")
    print(f"  Batch 0: 100 documents - UPLOADED")
    print(f"  Batches 1-6: {sum(b['count'] for b in batches)} documents - READY")
    print(f"  Total expected: 680 documents")

    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
