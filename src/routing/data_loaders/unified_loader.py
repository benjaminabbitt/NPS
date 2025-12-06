#!/usr/bin/env python3
"""
Unified Data Loader for VRP Trip Planning

Loads sites from multiple sources: NPS, World's Largest, Amusement Parks.
Converts all data types to Site objects compatible with VRP solver.
"""
from pathlib import Path
from typing import List, Optional, Dict

from core.site import Site
from .nps_loader import NPSSiteLoader
from .attraction_loader import WorldsLargestLoader, AmusementParkLoader
from .types import OperatingHours


class UnifiedDataLoader:
    """
    Unified loader for all attraction types using IoC pattern.

    Converts NPSSiteData, WorldsLargestData, and AmusementParkData
    into Site objects compatible with VRP solver.
    """

    def __init__(
        self,
        nps_loader: NPSSiteLoader,
        worlds_largest_loader: WorldsLargestLoader,
        park_loader: AmusementParkLoader
    ):
        """
        Initialize with injected data loaders.

        Args:
            nps_loader: Loader for NPS sites
            worlds_largest_loader: Loader for World's Largest attractions
            park_loader: Loader for amusement parks
        """
        self.nps_loader = nps_loader
        self.worlds_largest_loader = worlds_largest_loader
        self.park_loader = park_loader

    def load_nps_sites(self, nps_base_dir: Path, filter_visited: bool = False) -> List[Site]:
        """
        Load all NPS sites from 2-Enhanced Data/NPS directory.

        Args:
            nps_base_dir: Path to "2-Enhanced Data/NPS"
            filter_visited: If True, exclude sites marked as visited

        Returns:
            List of Site objects ready for VRP solver
        """
        nps_base_dir = Path(nps_base_dir)
        sites = []

        # Iterate through all site directories
        for site_dir in nps_base_dir.iterdir():
            if not site_dir.is_dir():
                continue

            try:
                site_data = self.nps_loader.load_from_directory(site_dir)

                # Skip if visited and filtering
                if filter_visited and site_data.visited:
                    continue

                # Convert to Site object
                site = site_data.site

                # Extract operating hours from first stamp
                if site_data.stamps and site_data.stamps[0].hours:
                    hours = OperatingHours.parse(site_data.stamps[0].hours)
                    if hours:
                        site.operating_hours = hours

                sites.append(site)

            except Exception as e:
                print(f"Warning: Failed to load {site_dir.name}: {e}")
                continue

        return sites

    def load_worlds_largest(
        self,
        file_path: Path,
        filter_completed: bool = False
    ) -> List[Site]:
        """
        Load World's Largest attractions.

        Args:
            file_path: Path to World's Largest.md
            filter_completed: If True, exclude completed attractions

        Returns:
            List of Site objects ready for VRP solver
        """
        try:
            data = self.worlds_largest_loader.load_from_file(file_path)
        except Exception as e:
            print(f"Warning: Failed to load World's Largest: {e}")
            return []

        sites = []
        for attraction in data.attractions:
            # Skip if completed and filtering
            if filter_completed and attraction.completed:
                continue

            # Convert to Site object
            if attraction.geocode:
                lat, lon = attraction.geocode
            else:
                continue  # Skip attractions without geocode

            site = Site(
                name=attraction.name,
                lat=lat,
                lon=lon,
                address=attraction.address
            )

            # Extract operating hours if available
            if attraction.hours:
                hours = OperatingHours.parse(attraction.hours)
                if hours:
                    site.operating_hours = hours

            sites.append(site)

        return sites

    def load_amusement_parks(self, parks_dir: Path) -> List[Site]:
        """
        Load all amusement parks.

        Args:
            parks_dir: Path to "2-Enhanced Data/Amusement Parks"

        Returns:
            List of Site objects (one per park)
        """
        parks_dir = Path(parks_dir)
        sites = []

        # Iterate through all park directories
        for park_dir in parks_dir.iterdir():
            if not park_dir.is_dir():
                continue

            try:
                park_data = self.park_loader.load_from_directory(park_dir)

                # Use park's site directly
                site = park_data.site

                # Extract operating hours if available
                if park_data.operating_hours:
                    hours = OperatingHours.parse(park_data.operating_hours)
                    if hours:
                        site.operating_hours = hours

                sites.append(site)

            except Exception as e:
                print(f"Warning: Failed to load park {park_dir.name}: {e}")
                continue

        return sites

    def load_all(
        self,
        nps_dir: Optional[Path] = None,
        worlds_largest_file: Optional[Path] = None,
        parks_dir: Optional[Path] = None,
        filter_visited: bool = False,
        filter_completed: bool = False
    ) -> Dict[str, List[Site]]:
        """
        Load all attraction types.

        Args:
            nps_dir: Path to NPS directory
            worlds_largest_file: Path to World's Largest file
            parks_dir: Path to Amusement Parks directory
            filter_visited: Exclude visited sites
            filter_completed: Exclude completed attractions

        Returns:
            Dictionary with keys: 'nps', 'worlds_largest', 'parks', 'all'
        """
        result = {
            'nps': [],
            'worlds_largest': [],
            'parks': [],
            'all': []
        }

        # Load NPS sites
        if nps_dir and nps_dir.exists():
            result['nps'] = self.load_nps_sites(nps_dir, filter_visited)
            result['all'].extend(result['nps'])

        # Load World's Largest
        if worlds_largest_file and worlds_largest_file.exists():
            result['worlds_largest'] = self.load_worlds_largest(
                worlds_largest_file, filter_completed
            )
            result['all'].extend(result['worlds_largest'])

        # Load Amusement Parks
        if parks_dir and parks_dir.exists():
            result['parks'] = self.load_amusement_parks(parks_dir)
            result['all'].extend(result['parks'])

        return result
