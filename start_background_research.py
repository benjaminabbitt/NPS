#!/usr/bin/env python3
"""
Master Orchestrator for Background NPS Research

Starts all background processes:
1. Geocoding
2. Web scraping
3. Chroma monitoring
"""

import subprocess
import time
import sys
from pathlib import Path


def main():
    print("="*70)
    print("Starting NPS Background Research System")
    print("="*70)
    print()
    print("This will start 3 concurrent processes:")
    print("  1. Geocoding (slow, accurate) - ~6-7 hours")
    print("  2. Web scraping for activities - ~2-3 hours")
    print("  3. Chroma MCP monitoring - continuous")
    print()
    print("Progress will be saved to:")
    print("  - geocode_cache.json (geocoding)")
    print("  - background_results.json (all results)")
    print("  - chroma_updates/ (Chroma batches)")
    print("  - summaries/ (human-readable summaries)")
    print("  - progress/ (progress reports)")
    print()

    venv_python = Path('.venv/Scripts/python.exe')

    # Start background processor
    print("[MAIN] Starting background processor...")
    bg_process = subprocess.Popen(
        [str(venv_python), 'background_processor.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    # Give it a moment to start
    time.sleep(2)

    # Start Chroma monitor
    print("[MAIN] Starting Chroma monitor...")
    chroma_process = subprocess.Popen(
        [str(venv_python), 'chroma_updater.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    print()
    print("="*70)
    print("All processes started!")
    print("="*70)
    print()
    print("To monitor progress:")
    print("  - Watch console output below")
    print("  - Check progress/progress_report.md")
    print("  - Check summaries/ for completed sites")
    print()
    print("Press Ctrl+C to stop all processes")
    print()
    print("="*70)
    print()

    try:
        # Stream output from both processes
        while True:
            # Read from background processor
            if bg_process.poll() is None:
                line = bg_process.stdout.readline()
                if line:
                    print(f"[BG] {line.rstrip()}")

            # Read from Chroma monitor
            if chroma_process.poll() is None:
                line = chroma_process.stdout.readline()
                if line:
                    print(f"[CM] {line.rstrip()}")

            # Check if both completed
            if bg_process.poll() is not None and chroma_process.poll() is not None:
                print("\n[MAIN] All processes completed!")
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n[MAIN] Stopping all processes...")
        bg_process.terminate()
        chroma_process.terminate()

        # Wait for clean shutdown
        bg_process.wait(timeout=5)
        chroma_process.wait(timeout=5)

        print("[MAIN] All processes stopped")

    print("\n" + "="*70)
    print("Background research system stopped")
    print("="*70)


if __name__ == '__main__':
    main()
