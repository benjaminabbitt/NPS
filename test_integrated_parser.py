#!/usr/bin/env python3
"""Test the updated NPSSiteLoader with integrated format"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src/routing'))

from data_loaders.factory import DataLoaderFactory

# Test with Acadia NP
loader = DataLoaderFactory.create_nps_loader()
site_dir = Path('2-Enhanced Data/NPS/Acadia NP')

print("Testing integrated format parser...")
print(f"Site directory: {site_dir}")

try:
    site_data = loader.load_from_directory(site_dir)

    print(f"\n✅ Successfully loaded site data")
    print(f"Site name: {site_data.site.name}")
    print(f"Visited: {site_data.visited}")
    print(f"Stamps: {len(site_data.stamps)}")
    print(f"  - Completed: {sum(1 for s in site_data.stamps if s.completed)}")
    print(f"Key Activities: {len(site_data.key_activities)}")
    print(f"  - Completed: {sum(1 for a in site_data.key_activities if a.completed)}")
    print(f"Hidden Gems: {len(site_data.hidden_gems)}")
    print(f"  - Completed: {sum(1 for g in site_data.hidden_gems if g.completed)}")
    print(f"Also Nearby: {len(site_data.also_nearby)}")
    print(f"  - Completed: {sum(1 for n in site_data.also_nearby if n.completed)}")
    print(f"Total time: {site_data.total_recommended_time_hours} hours")

    # Show some examples
    if site_data.stamps:
        print(f"\nFirst stamp: {site_data.stamps[0].location} (completed: {site_data.stamps[0].completed})")
    if site_data.key_activities:
        print(f"First activity: {site_data.key_activities[0].name} (completed: {site_data.key_activities[0].completed})")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
