#!/usr/bin/env python3
"""
Chroma MCP Incremental Updater

Monitors background processing results and updates Chroma MCP
incrementally for Claude-readable data access with minimal context.
"""

import json
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ChromaUpdater:
    """Updates Chroma MCP incrementally"""

    def __init__(self, results_file: str = 'background_results.json'):
        self.results_file = Path(results_file)
        self.last_update_count = 0
        self.geocode_updates = {}
        self.research_updates = {}
        self.batch_size = 50  # Update Chroma every 50 items

    def load_results(self) -> List[dict]:
        """Load current results"""
        if not self.results_file.exists():
            return []

        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def process_new_results(self, results: List[dict]):
        """Process new results since last check"""
        new_results = results[self.last_update_count:]

        if not new_results:
            return

        print(f"[CHROMA] Processing {len(new_results)} new results...")

        for result in new_results:
            if result['type'] == 'geocode':
                site_name = result['site_name']
                self.geocode_updates[site_name] = {
                    'lat': result['coords'][0],
                    'lon': result['coords'][1],
                    'geocoded_at': datetime.now().isoformat()
                }

            elif result['type'] == 'research':
                site_name = result['site_name']
                self.research_updates[site_name] = {
                    'key_activities': result.get('key_activities', []),
                    'hidden_gems': result.get('hidden_gems', []),
                    'nearby_attractions': result.get('nearby_attractions', []),
                    'sources': result.get('sources', []),
                    'researched_at': datetime.now().isoformat()
                }

        self.last_update_count = len(results)

        # Check if we should update Chroma
        if len(self.geocode_updates) + len(self.research_updates) >= self.batch_size:
            self.update_chroma_batch()

    def update_chroma_batch(self):
        """Update Chroma MCP with batched data"""
        print(f"[CHROMA] Updating Chroma MCP...")
        print(f"  - Geocode updates: {len(self.geocode_updates)}")
        print(f"  - Research updates: {len(self.research_updates)}")

        # Merge updates by site
        all_updates = {}

        # Add geocode data
        for site_name, data in self.geocode_updates.items():
            if site_name not in all_updates:
                all_updates[site_name] = {}
            all_updates[site_name].update(data)

        # Add research data
        for site_name, data in self.research_updates.items():
            if site_name not in all_updates:
                all_updates[site_name] = {}
            all_updates[site_name].update(data)

        # Save for external Chroma upload
        # (actual Chroma MCP calls would be made via Claude's tools)
        chroma_batch = {
            'timestamp': datetime.now().isoformat(),
            'update_count': len(all_updates),
            'updates': all_updates
        }

        chroma_file = Path('chroma_updates') / f'batch_{int(time.time())}.json'
        chroma_file.parent.mkdir(exist_ok=True)

        with open(chroma_file, 'w', encoding='utf-8') as f:
            json.dump(chroma_batch, f, indent=2)

        print(f"[CHROMA] Saved batch to {chroma_file}")

        # Create human-readable summary
        self.create_summary(all_updates)

        # Clear processed updates
        self.geocode_updates.clear()
        self.research_updates.clear()

    def create_summary(self, updates: Dict):
        """Create human-readable summary"""
        summary_dir = Path('summaries')
        summary_dir.mkdir(exist_ok=True)

        summary_file = summary_dir / f'summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'

        lines = [
            "# Site Research Summary",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Sites Updated:** {len(updates)}",
            "",
            "---",
            ""
        ]

        for site_name, data in updates.items():
            lines.extend([
                f"## {site_name}",
                ""
            ])

            if 'lat' in data and 'lon' in data:
                lines.append(f"**Location:** {data['lat']:.4f}, {data['lon']:.4f}")
                lines.append("")

            if 'key_activities' in data and data['key_activities']:
                lines.append("**Key Activities:**")
                for activity in data['key_activities']:
                    lines.append(f"- {activity['name']} ({activity['duration']})")
                lines.append("")

            if 'sources' in data and data['sources']:
                lines.append("**Sources:**")
                for source in data['sources']:
                    lines.append(f"- {source}")
                lines.append("")

            lines.append("---")
            lines.append("")

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"[CHROMA] Created summary: {summary_file}")

    def monitor(self, check_interval: int = 30):
        """Monitor results file and update Chroma incrementally"""
        print(f"[CHROMA] Starting monitoring (checking every {check_interval}s)...")

        try:
            while True:
                results = self.load_results()
                self.process_new_results(results)

                # Check for completion markers
                if results:
                    geocode_complete = any(r.get('type') == 'geocode_complete' for r in results)
                    research_complete = any(r.get('type') == 'research_complete' for r in results)

                    if geocode_complete and research_complete:
                        print("[CHROMA] Both processes complete!")
                        # Final batch update
                        if self.geocode_updates or self.research_updates:
                            self.update_chroma_batch()
                        break

                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n[CHROMA] Monitoring stopped by user")
            # Save any pending updates
            if self.geocode_updates or self.research_updates:
                self.update_chroma_batch()


def main():
    """Main monitoring loop"""
    print("="*70)
    print("Chroma MCP Incremental Updater")
    print("="*70)

    updater = ChromaUpdater()
    updater.monitor(check_interval=30)

    print("\n[CHROMA] Monitoring complete!")
    print("All updates saved to chroma_updates/")
    print("Human-readable summaries in summaries/")


if __name__ == '__main__':
    main()
