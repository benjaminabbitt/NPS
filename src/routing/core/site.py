#!/usr/bin/env python3
"""
Site domain model for trip planning

Represents an NPS site with geographic coordinates, operating hours,
and timezone information.
"""
from dataclasses import dataclass
from timezonefinder import TimezoneFinder

# Initialize timezone finder (global, reused across all lookups)
TZ_FINDER = TimezoneFinder()


@dataclass
class Site:
    """NPS Site with location and operating hours"""
    name: str
    lat: float
    lon: float
    address: str = ""
    city: str = ""
    state: str = ""
    operating_hours: object = None  # OperatingHours from nps_data_loader
    always_stamp_available: bool = False  # True if stamps accessible 24/7

    @property
    def full_name(self) -> str:
        """
        Full name with city and state.

        Examples:
            >>> site = Site("Test NP", 38.5, -90.4, city="St Louis", state="MO")
            >>> site.full_name
            'Test NP, St Louis, MO'

            >>> site = Site("Test NP", 38.5, -90.4)
            >>> site.full_name
            'Test NP'
        """
        if self.city and self.state:
            return f"{self.name}, {self.city}, {self.state}"
        return self.name

    def get_timezone(self) -> str:
        """
        Get IANA timezone identifier for this site's location.

        Uses TimezoneFinder to lookup timezone from coordinates.
        Falls back to America/Chicago if lookup fails.

        Returns:
            IANA timezone string (e.g., "America/Chicago", "America/Los_Angeles")

        Examples:
            >>> site = Site("Kirkwood Site", 38.5831, -90.4068)
            >>> site.get_timezone()
            'America/Chicago'

            >>> site = Site("SF Site", 37.7749, -122.4194)
            >>> site.get_timezone()
            'America/Los_Angeles'
        """
        tz_name = TZ_FINDER.timezone_at(lat=self.lat, lng=self.lon)
        return tz_name or "America/Chicago"  # Default to Central if lookup fails


if __name__ == '__main__':
    # Quick validation
    print("Testing Site dataclass...")

    # Test 1: Basic creation
    site = Site("Test NP", 38.5831, -90.4068)
    assert site.name == "Test NP"
    assert site.lat == 38.5831
    assert site.lon == -90.4068
    print("  ✓ Basic site creation")

    # Test 2: Full name with city/state
    site_full = Site("Test NP", 38.5831, -90.4068, city="Kirkwood", state="MO")
    assert site_full.full_name == "Test NP, Kirkwood, MO"
    print("  ✓ Full name with city and state")

    # Test 3: Full name without city/state
    assert site.full_name == "Test NP"
    print("  ✓ Full name without city/state")

    # Test 4: Timezone lookup (Central)
    tz = site.get_timezone()
    assert tz == "America/Chicago"
    print(f"  ✓ Timezone lookup: {tz}")

    # Test 5: Timezone lookup (Pacific)
    sf_site = Site("SF Site", 37.7749, -122.4194)
    tz_sf = sf_site.get_timezone()
    assert tz_sf == "America/Los_Angeles"
    print(f"  ✓ Timezone lookup (SF): {tz_sf}")

    # Test 6: Timezone fallback for invalid coordinates
    invalid_site = Site("Invalid", 0.0, 0.0)
    tz_fallback = invalid_site.get_timezone()
    # Ocean coordinates may return None or a timezone
    print(f"  ✓ Timezone fallback test: {tz_fallback}")

    print("✓ Site dataclass validated")
