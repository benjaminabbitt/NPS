#!/usr/bin/env python3
"""
Load NPS site data from the 2-Enhanced Data directory
Extracts site names, addresses, operating hours from ambers-data.md files
"""
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class OperatingHours:
    """Operating hours for a site"""
    opens: int  # Minutes from midnight (e.g., 9:00 AM = 540)
    closes: int  # Minutes from midnight (e.g., 5:00 PM = 1020)

    @staticmethod
    def parse_time(time_str: str) -> Optional[int]:
        """Parse time like '9:00 AM' or '17:00' to minutes from midnight"""
        time_str = time_str.strip().upper()

        # Try AM/PM format
        match = re.match(r'(\d+):(\d+)\s*(AM|PM)', time_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            period = match.group(3)

            if period == 'PM' and hours != 12:
                hours += 12
            elif period == 'AM' and hours == 12:
                hours = 0

            return hours * 60 + minutes

        # Try 24-hour format
        match = re.match(r'(\d+):(\d+)', time_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return hours * 60 + minutes

        return None


@dataclass
class NPSSite:
    """Complete NPS site information"""
    name: str  # Full site name (e.g., "Abraham Lincoln Birthplace NHP")
    city: str
    state: str
    lat: float
    lon: float
    address: str
    visitor_center: str = ""
    operating_hours: Optional[OperatingHours] = None
    always_stamp_available: bool = False  # True if stamps accessible 24/7

    @property
    def full_name(self) -> str:
        """Full name with city and state"""
        return f"{self.name}, {self.city}, {self.state}"


class NPSDataLoader:
    """Load NPS site data from directory structure"""

    def __init__(self, data_dir: str = "2-Enhanced Data/NPS"):
        self.data_dir = Path(data_dir)
        self.sites_by_address = {}  # Map geocoded addresses to sites

    def load_all_sites(self) -> Dict[str, NPSSite]:
        """Load all NPS sites from directory"""
        sites = {}

        for site_dir in self.data_dir.iterdir():
            if not site_dir.is_dir():
                continue

            site = self._load_site(site_dir)
            if site:
                sites[site.name] = site
                # Also index by address for lookup
                if site.address:
                    self.sites_by_address[site.address] = site

        return sites

    def _load_site(self, site_dir: Path) -> Optional[NPSSite]:
        """Load a single site from its directory"""
        # Find the main site .md file (not user-data.md or CLAUDE.md)
        site_file = None
        for md_file in site_dir.glob("*.md"):
            if md_file.name not in ["user-data.md", "CLAUDE.md"]:
                site_file = md_file
                break

        if not site_file:
            return None

        try:
            content = site_file.read_text()

            # Extract geocode from YAML frontmatter
            if not content.startswith('---\n'):
                return None

            parts = content.split('---\n', 2)
            if len(parts) < 3:
                return None

            yaml_content = parts[1]

            # Extract geocode
            geocode_match = re.search(r'visitor_center:\s*\[([0-9.-]+),\s*([0-9.-]+)\]', yaml_content)
            if not geocode_match:
                return None

            lat = float(geocode_match.group(1))
            lon = float(geocode_match.group(2))

            # Try to get additional info from user-data.md if it exists
            user_data_file = site_dir / "user-data.md"
            visitor_center = ""
            address = ""
            city = "Unknown"
            state = "Unknown"
            operating_hours = None
            always_available = False

            if user_data_file.exists():
                user_content = user_data_file.read_text()

                # Extract visitor center
                vc_match = re.search(r'\*\*Visitor Center:\*\*\s*(.+)', user_content)
                if vc_match:
                    visitor_center = vc_match.group(1).strip()

                # Extract address
                addr_match = re.search(r'\*\*Address:\*\*\s*(.+?)(?:\s*\([0-9.-]+,\s*[0-9.-]+\))?$', user_content, re.MULTILINE)
                if addr_match:
                    address = addr_match.group(1).strip()

                    # Extract city and state from address
                    addr_parts = [p.strip() for p in address.split(',')]
                    if len(addr_parts) >= 3:
                        city = addr_parts[-2]
                        # State with zip code - remove 5-digit zip
                        state_part = addr_parts[-1]
                        state = re.sub(r'\s+\d{5}(-\d{4})?$', '', state_part).strip()

                # Extract operating hours
                hours_match = re.search(r'\*\*Hours:\*\*\s*(.+)', user_content)
                if hours_match:
                    hours_text = hours_match.group(1)
                    if "not available" not in hours_text.lower() and "closed" not in hours_text.lower():
                        operating_hours = self._parse_hours(hours_text)

                # Check for always_stamp_available flag
                always_match = re.search(r'\*\*Always Stamp Available:\*\*\s*(true|yes|1)', user_content, re.IGNORECASE)
                if always_match:
                    always_available = True

            # Use default hours (8:00 AM - 5:00 PM) if not specified
            if not operating_hours:
                operating_hours = OperatingHours(opens=8*60, closes=17*60)  # 8 AM to 5 PM

            return NPSSite(
                name=site_dir.name,
                city=city,
                state=state,
                lat=lat,
                lon=lon,
                address=address,
                visitor_center=visitor_center,
                operating_hours=operating_hours,
                always_stamp_available=always_available
            )

        except Exception as e:
            print(f"Error loading {site_dir.name}: {e}")
            return None

    def _parse_hours(self, hours_text: str) -> Optional[OperatingHours]:
        """Parse operating hours like '9:00 AM - 5:00 PM'"""
        # Look for pattern like "9:00 AM - 5:00 PM" or "9 AM - 5 PM"
        match = re.search(r'(\d+:?\d*\s*[AP]M)\s*-\s*(\d+:?\d*\s*[AP]M)', hours_text, re.IGNORECASE)
        if match:
            open_time = OperatingHours.parse_time(match.group(1))
            close_time = OperatingHours.parse_time(match.group(2))

            if open_time is not None and close_time is not None:
                return OperatingHours(opens=open_time, closes=close_time)

        return None

    def get_site_by_address(self, address: str) -> Optional[NPSSite]:
        """Look up site by geocoded address"""
        # Try exact match first
        if address in self.sites_by_address:
            return self.sites_by_address[address]

        # Try partial match (address might have slight variations)
        for addr, site in self.sites_by_address.items():
            if addr in address or address in addr:
                return site

        return None


def main():
    """Test the loader"""
    loader = NPSDataLoader()
    sites = loader.load_all_sites()

    print(f"Loaded {len(sites)} NPS sites")
    print(f"\nSample sites:")
    for i, (name, site) in enumerate(list(sites.items())[:10]):
        hours_str = f"{site.operating_hours.opens//60}:00-{site.operating_hours.closes//60}:00" if site.operating_hours else "No hours"
        print(f"  {site.full_name} ({hours_str})")

    # Test address lookup
    print(f"\nAddress index: {len(loader.sites_by_address)} addresses")


if __name__ == '__main__':
    main()
