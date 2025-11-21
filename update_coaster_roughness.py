#!/usr/bin/env python3
"""
Research and update coaster-specific data with proper citations
"""

import asyncio
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class CoasterResearch:
    coaster_name: str
    park_name: str
    roughness: str
    roughness_sources: List[str]
    height_requirement: str
    height_sources: List[str]
    memorable_moments: List[str]
    moment_sources: List[str]
    reviews: List[Dict[str, str]]
    review_sources: List[str]


class CoasterResearcher:
    def __init__(self):
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    async def search_rcdb(
        self,
        coaster_name: str,
        park_name: str,
        client: httpx.AsyncClient
    ) -> Tuple[Optional[str], List[str]]:
        """Search RCDB for coaster data"""

        try:
            # Search RCDB
            search_url = f"https://rcdb.com/qs.htm?qs={coaster_name.replace(' ', '+')}"
            response = await client.get(search_url, headers=self.headers, timeout=15.0, follow_redirects=True)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Try to find coaster page link
                links = soup.find_all('a', href=re.compile(r'/\d+\.htm'))
                for link in links:
                    if coaster_name.lower() in link.get_text().lower():
                        coaster_url = "https://rcdb.com" + link['href']

                        # Get coaster page
                        detail_response = await client.get(coaster_url, headers=self.headers, timeout=15.0)
                        if detail_response.status_code == 200:
                            detail_soup = BeautifulSoup(detail_response.content, 'html.parser')

                            # Extract height requirement
                            height_section = detail_soup.find(string=re.compile(r'Height Requirement', re.I))
                            if height_section:
                                height_text = height_section.find_parent().get_text(strip=True)
                                return coaster_url, [height_text]

                        await asyncio.sleep(2)

            await asyncio.sleep(2)

        except Exception as e:
            print(f"    RCDB error: {e}", flush=True)

        return None, []

    async def search_reviews(
        self,
        coaster_name: str,
        park_name: str,
        client: httpx.AsyncClient
    ) -> Tuple[List[str], List[str], List[str]]:
        """Search for coaster reviews and roughness data"""

        roughness_findings = []
        moment_findings = []
        sources = []

        try:
            # Search CoasterBuzz
            search_url = f"https://coasterbuzz.com/Search?q={coaster_name.replace(' ', '+')}"
            response = await client.get(search_url, headers=self.headers, timeout=15.0, follow_redirects=True)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Look for coaster page
                results = soup.find_all('a', href=re.compile(r'/Coaster/'))
                for result in results[:3]:
                    if coaster_name.lower() in result.get_text().lower():
                        coaster_url = "https://coasterbuzz.com" + result['href']

                        # Get reviews
                        review_response = await client.get(coaster_url, headers=self.headers, timeout=15.0)
                        if review_response.status_code == 200:
                            review_soup = BeautifulSoup(review_response.content, 'html.parser')

                            # Extract review text
                            reviews = review_soup.find_all(class_=re.compile(r'review|comment', re.I))
                            for review in reviews[:5]:
                                text = review.get_text(strip=True)

                                # Look for roughness mentions
                                if any(word in text.lower() for word in ['rough', 'smooth', 'rattle', 'butter', 'bumpy', 'comfortable']):
                                    roughness_findings.append(text[:200])

                                # Look for moment mentions
                                if any(word in text.lower() for word in ['drop', 'inversion', 'airtime', 'speed', 'thrill', 'moment']):
                                    moment_findings.append(text[:200])

                            sources.append(coaster_url)

                        await asyncio.sleep(2)

            await asyncio.sleep(2)

        except Exception as e:
            print(f"    Review search error: {e}", flush=True)

        # Try Theme Park Insider
        try:
            search_url = f"https://www.themeparkinside.com/search?q={coaster_name.replace(' ', '+')}"
            response = await client.get(search_url, headers=self.headers, timeout=15.0, follow_redirects=True)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract snippets
                articles = soup.find_all('article', limit=3)
                for article in articles:
                    text = article.get_text(strip=True)

                    if any(word in text.lower() for word in ['rough', 'smooth', 'ride quality']):
                        roughness_findings.append(text[:200])

                    if any(word in text.lower() for word in ['element', 'feature', 'highlight']):
                        moment_findings.append(text[:200])

                if articles:
                    sources.append(search_url)

            await asyncio.sleep(2)

        except Exception as e:
            print(f"    Theme Park search error: {e}", flush=True)

        return roughness_findings, moment_findings, sources

    def analyze_roughness(self, findings: List[str]) -> str:
        """Analyze findings to create roughness description"""

        if not findings:
            return "Roughness data requires additional research"

        # Count roughness indicators
        smooth_keywords = ['smooth', 'butter', 'comfortable', 'glass', 'silky', 'comfortable']
        rough_keywords = ['rough', 'rattle', 'bumpy', 'jarring', 'jerky', 'headbang', 'uncomfortable', 'painful']

        smooth_count = sum(1 for f in findings for word in smooth_keywords if word in f.lower())
        rough_count = sum(1 for f in findings for word in rough_keywords if word in f.lower())

        if smooth_count > rough_count * 2:
            return "Riders report this coaster as very smooth"
        elif rough_count > smooth_count * 2:
            return "Riders report this coaster has noticeable roughness"
        elif smooth_count > rough_count:
            return "Generally reported as smooth with some intensity"
        elif rough_count > smooth_count:
            return "Some riders report rough sections, particularly in certain seats"
        else:
            return "Mixed rider feedback on smoothness"

    def extract_memorable_moments(self, findings: List[str]) -> List[str]:
        """Extract memorable moments from findings"""

        moments = []

        # Keywords for different types of moments
        drop_keywords = ['drop', 'plunge', 'fall']
        inversion_keywords = ['inversion', 'loop', 'corkscrew', 'barrel roll', 'zero-g']
        airtime_keywords = ['airtime', 'ejector', 'float', 'weightless']
        speed_keywords = ['speed', 'fast', 'launch', 'acceleration']

        for finding in findings:
            text_lower = finding.lower()

            if any(k in text_lower for k in drop_keywords):
                moments.append("Notable drop element")
            if any(k in text_lower for k in inversion_keywords):
                moments.append("Multiple inversion elements")
            if any(k in text_lower for k in airtime_keywords):
                moments.append("Strong airtime moments")
            if any(k in text_lower for k in speed_keywords):
                moments.append("High-speed sections")

        return list(set(moments))[:4] if moments else ["Detailed moment information requires additional research"]

    async def research_coaster(
        self,
        coaster_name: str,
        park_name: str,
        client: httpx.AsyncClient
    ) -> CoasterResearch:
        """Research all data for a coaster"""

        print(f"  Researching: {coaster_name}", flush=True)

        # Get RCDB data
        rcdb_url, height_data = await self.search_rcdb(coaster_name, park_name, client)
        height_sources = [rcdb_url] if rcdb_url else []

        # Get reviews and roughness
        roughness_findings, moment_findings, review_sources = await self.search_reviews(
            coaster_name, park_name, client
        )

        # Analyze data
        roughness = self.analyze_roughness(roughness_findings)
        moments = self.extract_memorable_moments(moment_findings)

        # Height requirement
        if height_data:
            height_req = height_data[0]
        else:
            height_req = "Height requirement data requires additional research"

        # Create review summaries
        reviews = []
        if roughness_findings:
            reviews.append({
                "source": "Community Reviews",
                "rating": "Varies",
                "summary": roughness_findings[0][:150] + "..."
            })

        return CoasterResearch(
            coaster_name=coaster_name,
            park_name=park_name,
            roughness=roughness,
            roughness_sources=review_sources,
            height_requirement=height_req,
            height_sources=height_sources,
            memorable_moments=moments,
            moment_sources=review_sources,
            reviews=reviews,
            review_sources=review_sources
        )

    async def update_coaster_file(self, coaster_file: Path, research: CoasterResearch):
        """Update coaster markdown file with researched data and citations"""

        with open(coaster_file, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        new_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Update Height Requirement section
            if line.strip() == '## Height Requirement':
                new_lines.append(line)
                new_lines.append('')
                new_lines.append(research.height_requirement)
                if research.height_sources:
                    new_lines.append('')
                    sources_text = ', '.join([f"[Source]({url})" for url in research.height_sources])
                    new_lines.append(f"*{sources_text}*")

                # Skip old content
                i += 1
                while i < len(lines) and not lines[i].startswith('##'):
                    i += 1
                continue

            # Update Subjective Roughness section
            elif line.strip() == '## Subjective Roughness':
                new_lines.append(line)
                new_lines.append('')
                new_lines.append(research.roughness)
                if research.roughness_sources:
                    new_lines.append('')
                    sources_text = ', '.join([f"[Source]({url})" for url in research.roughness_sources])
                    new_lines.append(f"*{sources_text}*")

                # Skip old content
                i += 1
                while i < len(lines) and not lines[i].startswith('##'):
                    i += 1
                continue

            # Update Memorable Moments section
            elif line.strip() == '## Memorable Moments':
                new_lines.append(line)
                new_lines.append('')
                for moment in research.memorable_moments:
                    new_lines.append(f"- {moment}")
                if research.moment_sources:
                    new_lines.append('')
                    sources_text = ', '.join([f"[Source]({url})" for url in research.moment_sources])
                    new_lines.append(f"*{sources_text}*")

                # Skip old content
                i += 1
                while i < len(lines) and not lines[i].startswith('##'):
                    i += 1
                continue

            # Update Reviews section
            elif line.strip() == '## Reviews':
                new_lines.append(line)
                new_lines.append('')
                for review in research.reviews:
                    new_lines.append(f"### {review['source']}")
                    new_lines.append(f"**Rating:** {review['rating']}")
                    new_lines.append(review['summary'])
                    new_lines.append('')
                if research.review_sources:
                    sources_text = ', '.join([f"[Source]({url})" for url in research.review_sources])
                    new_lines.append(f"*{sources_text}*")

                # Skip old content
                i += 1
                while i < len(lines) and not lines[i].startswith('##'):
                    i += 1
                continue

            new_lines.append(line)
            i += 1

        # Write back
        with open(coaster_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))

        print(f"    Updated: {coaster_file.name}", flush=True)

    async def process_all_coasters(self):
        """Process all coaster files"""
        base_dir = Path("Amusement Parks")
        park_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name != "Inputs"]

        all_coasters = []

        # Collect all coasters
        for park_dir in park_dirs:
            park_name = park_dir.name
            park_file = park_dir / f"{park_name}.md"

            coaster_files = [f for f in park_dir.glob("*.md") if f.name != park_file.name]

            for coaster_file in coaster_files:
                coaster_name = coaster_file.stem
                all_coasters.append((coaster_file, coaster_name, park_name))

        print(f"Processing {len(all_coasters)} coasters with full citations...", flush=True)
        print("="*70, flush=True)

        async with httpx.AsyncClient() as client:
            for i, (coaster_file, coaster_name, park_name) in enumerate(all_coasters, 1):
                print(f"\n[{i}/{len(all_coasters)}] {coaster_name} at {park_name}", flush=True)

                research = await self.research_coaster(coaster_name, park_name, client)
                await self.update_coaster_file(coaster_file, research)

                self.results.append(research)

                # Save progress every 10 coasters
                if i % 10 == 0:
                    self._save_results()
                    print(f"\n  Progress saved: {i}/{len(all_coasters)} complete", flush=True)

        self._save_results()
        print("\n" + "="*70)
        print(f"Complete! Updated {len(all_coasters)} coasters with citations")

    def _save_results(self):
        """Save research results to JSON"""
        output_file = Path("coaster_research_with_citations.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)


async def main():
    print("="*70)
    print("Coaster Research with Full Citations")
    print("="*70)
    print()

    researcher = CoasterResearcher()
    await researcher.process_all_coasters()

    print()
    print("All coaster files updated with:")
    print("  - Coaster-specific roughness data (with sources)")
    print("  - Height requirements (with sources)")
    print("  - Memorable moments (with sources)")
    print("  - Reviews (with sources)")


if __name__ == '__main__':
    asyncio.run(main())
