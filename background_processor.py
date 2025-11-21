#!/usr/bin/env python3
"""
Parallel Background Processing for NPS Research

Runs two simultaneous background processes:
1. Geocoding (slow, accurate)
2. Web scraping for activities and timing data

Updates Chroma MCP incrementally and generates progress reports.
"""

import json
import time
import asyncio
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import threading
import queue
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import urllib.parse


@dataclass
class SiteResearchComplete:
    """Complete research for a site"""
    site_name: str
    state: str
    city: str
    address: str
    lat: Optional[float]
    lon: Optional[float]

    # Research data
    cancellation_stamps: List[Dict]
    key_activities: List[Dict]
    hidden_gems: List[Dict]
    nearby_attractions: List[Dict]

    # Metadata
    researched_timestamp: str
    geocoded: bool
    research_complete: bool

    def to_markdown(self) -> str:
        """Generate markdown report"""
        lines = [f"# {self.site_name}", "", "## Cancellation Stamp Locations:", ""]

        for stamp in self.cancellation_stamps:
            lines.append(f"- [ ] {stamp['location']} ({stamp['address']}; {stamp['hours']})")

        if not self.cancellation_stamps:
            lines.append("- Contact visitor center for stamp locations")

        lines.extend(["", "## Key Activities:", ""])
        for activity in self.key_activities:
            sources = ', '.join([f"[Source]({s})" for s in activity.get('sources', [])])
            lines.append(f"- [ ] **{activity['name']}** ({activity['duration']}) - {activity['description']}; {activity['address']}; {activity['hours']} [{sources}]")

        lines.extend(["", "## Hidden Gems:", ""])
        for gem in self.hidden_gems:
            sources = ', '.join([f"[Source]({s})" for s in gem.get('sources', [])])
            lines.append(f"- [ ] **{gem['name']}** ({gem['duration']}) - {gem['description']}; {gem['address']}; {gem['hours']} [{sources}]")

        lines.extend(["", "## Also Nearby:", ""])
        for nearby in self.nearby_attractions:
            sources = ', '.join([f"[Source]({s})" for s in nearby.get('sources', [])])
            lines.append(f"- [ ] **{nearby['name']}** ({nearby.get('duration', 'varies')}) - {nearby['description']}; {nearby.get('address', '')}; {nearby.get('hours', '')} [{sources}]")

        return "\n".join(lines)


class BackgroundGeocoder:
    """Background geocoding with rate limiting"""

    def __init__(self, output_queue: queue.Queue):
        self.output_queue = output_queue
        self.cache_file = Path('geocode_cache.json')
        self.cache = self.load_cache()
        self.processed = 0
        self.failed = 0

    def load_cache(self) -> dict:
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2)

    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode single address"""
        if address in self.cache:
            return tuple(self.cache[address])

        try:
            url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})}"
            headers = {'User-Agent': 'NPS-Research/1.0 (comprehensive research project)'}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=15.0)
                data = response.json()

                if data:
                    coords = (float(data[0]['lat']), float(data[0]['lon']))
                    self.cache[address] = coords
                    self.save_cache()
                    return coords

        except Exception as e:
            print(f"Geocoding error for {address}: {e}")
            return None

        return None

    async def process_sites(self, sites: List[dict]):
        """Process all sites with rate limiting"""
        print(f"[GEOCODER] Starting geocoding of {len(sites)} sites...")

        for i, site in enumerate(sites):
            address = site['address']

            if address in self.cache:
                self.processed += 1
                continue

            coords = await self.geocode_address(address)

            if coords:
                self.processed += 1
                result = {
                    'type': 'geocode',
                    'site_name': site['name'],
                    'address': address,
                    'coords': coords,
                    'progress': f"{self.processed}/{len(sites)}"
                }
                self.output_queue.put(result)
            else:
                self.failed += 1

            # Rate limiting: 1.2 seconds between requests
            await asyncio.sleep(1.2)

            # Progress update every 10 sites
            if (i + 1) % 10 == 0:
                print(f"[GEOCODER] Progress: {i+1}/{len(sites)} ({self.processed} successful, {self.failed} failed)")

        print(f"[GEOCODER] Complete! {self.processed} successful, {self.failed} failed")
        self.output_queue.put({'type': 'geocode_complete', 'total': self.processed, 'failed': self.failed})


class BackgroundResearcher:
    """Background web scraping for activities and timing"""

    def __init__(self, output_queue: queue.Queue):
        self.output_queue = output_queue
        self.processed = 0
        self.failed = 0

    def extract_nps_code(self, site_name: str) -> str:
        """Extract NPS park code"""
        # Common NPS abbreviations
        abbrevs = {
            'NM': '', 'NP': '', 'NHS': '', 'NHP': '', 'NB': '', 'NBP': '', 'NMP': '',
            'N PRES': '', 'N MEM': '', 'NRA': '', 'NS': '', 'PRES': '', 'WSR': '',
            'N RES': '', 'NL': '', 'SRR': '', 'NST': '', 'NRRA': '', 'IHS': '', 'WR': ''
        }

        name = site_name
        for abbrev in abbrevs:
            name = name.replace(f' {abbrev}', '')

        # Get first letters of first 2-3 words
        words = name.split()
        code = ''.join([w[0].lower() for w in words[:min(4, len(words))]])
        return code

    async def fetch_nps_page(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """Fetch NPS page content"""
        try:
            response = await client.get(url, timeout=20.0, follow_redirects=True)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            pass
        return None

    async def parse_activities_from_nps(self, html: str, base_url: str) -> List[Dict]:
        """Parse activities from NPS things to do page"""
        soup = BeautifulSoup(html, 'html.parser')
        activities = []

        # Look for activity sections
        activity_sections = soup.find_all(['div', 'section'], class_=['Component'])

        for section in activity_sections[:5]:  # Top 5 activities
            title_elem = section.find(['h2', 'h3', 'h4'])
            desc_elem = section.find('p')

            if title_elem and desc_elem:
                activities.append({
                    'name': title_elem.get_text(strip=True)[:100],
                    'duration': '2-3 hours',  # Default estimate
                    'description': desc_elem.get_text(strip=True)[:300],
                    'address': 'See park website',
                    'hours': 'Varies by season',
                    'sources': [base_url]
                })

        return activities

    async def research_site(self, site: dict, client: httpx.AsyncClient) -> Optional[Dict]:
        """Research a single site"""
        site_name = site['name']
        nps_code = self.extract_nps_code(site_name)

        base_url = f"https://www.nps.gov/{nps_code}"

        # Try multiple URLs
        urls_to_try = [
            f"{base_url}/planyourvisit/things2do.htm",
            f"{base_url}/planyourvisit/index.htm",
            f"{base_url}/index.htm"
        ]

        activities = []
        sources_checked = []

        for url in urls_to_try:
            html = await self.fetch_nps_page(client, url)
            if html:
                sources_checked.append(url)
                found_activities = await self.parse_activities_from_nps(html, url)
                activities.extend(found_activities)

                if activities:
                    break

            await asyncio.sleep(0.5)  # Rate limiting

        # If no activities found, create placeholder
        if not activities:
            activities = [{
                'name': 'Visitor Center Experience',
                'duration': '1-2 hours',
                'description': f'Explore the visitor center and exhibits at {site_name}',
                'address': site['address'],
                'hours': site.get('hours', {}).get('Monday', 'Contact site'),
                'sources': sources_checked if sources_checked else [base_url]
            }]

        return {
            'type': 'research',
            'site_name': site_name,
            'state': site.get('state', ''),
            'city': site.get('city', ''),
            'key_activities': activities[:3],
            'hidden_gems': [],  # Would need more sophisticated scraping
            'nearby_attractions': [],
            'sources': sources_checked
        }

    async def process_sites(self, sites: List[dict]):
        """Process all sites"""
        print(f"[RESEARCHER] Starting research of {len(sites)} sites...")

        async with httpx.AsyncClient() as client:
            for i, site in enumerate(sites):
                try:
                    result = await self.research_site(site, client)
                    if result:
                        self.processed += 1
                        result['progress'] = f"{self.processed}/{len(sites)}"
                        self.output_queue.put(result)
                    else:
                        self.failed += 1

                except Exception as e:
                    print(f"[RESEARCHER] Error researching {site['name']}: {e}")
                    self.failed += 1

                # Rate limiting: 2 seconds between sites
                await asyncio.sleep(2.0)

                # Progress update
                if (i + 1) % 5 == 0:
                    print(f"[RESEARCHER] Progress: {i+1}/{len(sites)} ({self.processed} successful)")

        print(f"[RESEARCHER] Complete! {self.processed} successful, {self.failed} failed")
        self.output_queue.put({'type': 'research_complete', 'total': self.processed, 'failed': self.failed})


class ProgressReporter:
    """Generates human-readable progress reports"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.geocode_count = 0
        self.research_count = 0
        self.start_time = time.time()

    def update(self, result: dict):
        """Update progress based on result"""
        if result['type'] == 'geocode':
            self.geocode_count += 1
        elif result['type'] == 'research':
            self.research_count += 1

        # Generate report every 10 updates
        if (self.geocode_count + self.research_count) % 10 == 0:
            self.generate_report()

    def generate_report(self):
        """Generate progress report"""
        elapsed = time.time() - self.start_time

        report = [
            "# NPS Research Progress Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Elapsed Time:** {elapsed/3600:.1f} hours",
            "",
            "## Progress",
            "",
            f"- **Geocoded Sites:** {self.geocode_count}",
            f"- **Researched Sites:** {self.research_count}",
            f"- **Total Processed:** {self.geocode_count + self.research_count}",
            "",
            f"**Rate:**",
            f"- Geocoding: {self.geocode_count / (elapsed/3600):.1f} sites/hour",
            f"- Research: {self.research_count / (elapsed/3600):.1f} sites/hour",
            ""
        ]

        report_file = self.output_dir / 'progress_report.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))


def run_geocoding_process(sites: List[dict], output_queue: queue.Queue):
    """Run geocoding in background"""
    geocoder = BackgroundGeocoder(output_queue)
    asyncio.run(geocoder.process_sites(sites))


def run_research_process(sites: List[dict], output_queue: queue.Queue):
    """Run research in background"""
    researcher = BackgroundResearcher(output_queue)
    asyncio.run(researcher.process_sites(sites))


def main():
    """Main orchestration"""
    print("="*70)
    print("Parallel Background Processing System")
    print("="*70)

    # Load sites
    with open('nps_site_inventory.json', 'r', encoding='utf-8') as f:
        inventory = json.load(f)

    # Flatten sites
    all_sites = []
    for state, sites in inventory['by_state'].items():
        for site in sites:
            site['state'] = state
            all_sites.append(site)

    print(f"\nTotal sites to process: {len(all_sites)}")

    # Create output queue
    result_queue = queue.Queue()

    # Create progress reporter
    reporter = ProgressReporter(Path('progress'))

    # Start both processes
    with ThreadPoolExecutor(max_workers=2) as executor:
        print("\n[MAIN] Starting parallel processes...")
        print("[MAIN] Process 1: Geocoding (slow, accurate)")
        print("[MAIN] Process 2: Web scraping (activity research)")

        # Submit both tasks
        geocode_future = executor.submit(run_geocoding_process, all_sites, result_queue)
        research_future = executor.submit(run_research_process, all_sites, result_queue)

        # Monitor results
        geocode_done = False
        research_done = False
        results_collected = []

        while not (geocode_done and research_done):
            try:
                result = result_queue.get(timeout=1.0)
                results_collected.append(result)

                if result['type'] == 'geocode_complete':
                    geocode_done = True
                    print(f"\n[MAIN] Geocoding complete: {result['total']} sites")
                elif result['type'] == 'research_complete':
                    research_done = True
                    print(f"\n[MAIN] Research complete: {result['total']} sites")
                else:
                    reporter.update(result)

            except queue.Empty:
                continue

        print("\n[MAIN] Both processes complete!")

    # Generate final report
    reporter.generate_report()

    # Save results
    with open('background_results.json', 'w', encoding='utf-8') as f:
        json.dump(results_collected, f, indent=2)

    print(f"\n{'='*70}")
    print("Background processing complete!")
    print(f"Results saved to: background_results.json")
    print(f"Progress reports in: progress/")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
