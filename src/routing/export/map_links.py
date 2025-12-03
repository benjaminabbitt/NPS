#!/usr/bin/env python3
"""
Map link generation for trip routes

Interface-based design for multiple map providers.
"""
from typing import List, Tuple, Protocol


class RouteMapProvider(Protocol):
    """Protocol for route map link generators"""

    def create_route_link(self, waypoints: List[Tuple[float, float]]) -> str:
        """Create a shareable route link from waypoints"""
        ...


class OpenStreetMapProvider:
    """OpenStreetMap route link generator using FOSSGIS OSRM"""

    def create_route_link(self, waypoints: List[Tuple[float, float]]) -> str:
        """
        Create OpenStreetMap Directions link with multiple waypoints.

        Uses FOSSGIS OSRM routing engine for car navigation.

        Args:
            waypoints: List of (lat, lon) tuples representing route stops

        Returns:
            OpenStreetMap URL with all waypoints

        Examples:
            >>> osm = OpenStreetMapProvider()
            >>> waypoints = [(38.5831, -90.4068)]
            >>> link = osm.create_route_link(waypoints)
            >>> link.startswith("https://www.openstreetmap.org/directions?")
            True
            >>> "38.5831,-90.4068" in link
            True

            >>> waypoints = [(38.5831, -90.4068), (38.6247, -90.1848)]
            >>> link = osm.create_route_link(waypoints)
            >>> "38.5831,-90.4068;38.6247,-90.1848" in link
            True
        """
        route_points = ";".join([f"{lat},{lon}" for lat, lon in waypoints])
        return f"https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={route_points}"


class GoogleMapsProvider:
    """Google Maps route link generator"""

    def create_route_link(self, waypoints: List[Tuple[float, float]]) -> str:
        """
        Create Google Maps directions link with multiple waypoints.

        Args:
            waypoints: List of (lat, lon) tuples representing route stops

        Returns:
            Google Maps URL with all waypoints, or empty string if no waypoints

        Examples:
            >>> gmaps = GoogleMapsProvider()
            >>> waypoints = []
            >>> gmaps.create_route_link(waypoints)
            ''

            >>> waypoints = [(38.5831, -90.4068)]
            >>> link = gmaps.create_route_link(waypoints)
            >>> link.startswith("https://www.google.com/maps/dir/")
            True
            >>> "38.5831,-90.4068" in link
            True

            >>> waypoints = [(38.5831, -90.4068), (38.6247, -90.1848)]
            >>> link = gmaps.create_route_link(waypoints)
            >>> "38.5831,-90.4068" in link
            True
            >>> "38.6247,-90.1848" in link
            True
        """
        if not waypoints:
            return ""

        start = waypoints[0]
        end = waypoints[-1]
        url = f"https://www.google.com/maps/dir/{start[0]},{start[1]}"

        # Add intermediate waypoints
        for lat, lon in waypoints[1:-1]:
            url += f"/{lat},{lon}"

        url += f"/{end[0]},{end[1]}"
        return url


# Convenience functions for backward compatibility
def create_osm_route_link(waypoints: List[Tuple[float, float]]) -> str:
    """Create OpenStreetMap route link (convenience function)"""
    return OpenStreetMapProvider().create_route_link(waypoints)


def create_google_maps_link(waypoints: List[Tuple[float, float]]) -> str:
    """Create Google Maps route link (convenience function)"""
    return GoogleMapsProvider().create_route_link(waypoints)


if __name__ == '__main__':
    # Quick validation
    print("Testing OpenStreetMapProvider...")

    osm = OpenStreetMapProvider()

    # Test 1: Single waypoint
    waypoints = [(38.5831, -90.4068)]
    link = osm.create_route_link(waypoints)
    assert link.startswith("https://www.openstreetmap.org/directions?")
    assert "38.5831,-90.4068" in link
    print(f"  Single waypoint: {link}")

    # Test 2: Multiple waypoints
    waypoints = [(38.5831, -90.4068), (38.6247, -90.1848)]
    link = osm.create_route_link(waypoints)
    assert "38.5831,-90.4068;38.6247,-90.1848" in link
    print(f"  Multiple waypoints: {link}")

    print("✓ OpenStreetMapProvider validated")

    print("\nTesting GoogleMapsProvider...")

    gmaps = GoogleMapsProvider()

    # Test 1: Empty waypoints
    link = gmaps.create_route_link([])
    assert link == ""
    print("  Empty waypoints: (empty string)")

    # Test 2: Single waypoint
    waypoints = [(38.5831, -90.4068)]
    link = gmaps.create_route_link(waypoints)
    assert link.startswith("https://www.google.com/maps/dir/")
    assert "38.5831,-90.4068" in link
    print(f"  Single waypoint: {link}")

    # Test 3: Multiple waypoints
    waypoints = [(38.5831, -90.4068), (38.6247, -90.1848), (38.6270, -90.1994)]
    link = gmaps.create_route_link(waypoints)
    assert "38.5831,-90.4068" in link
    assert "38.6247,-90.1848" in link
    # Python drops trailing zeros: 38.6270 -> 38.627
    assert "38.627,-90.1994" in link
    print(f"  Multiple waypoints: {link}")

    print("✓ GoogleMapsProvider validated")

    print("\nTesting backward compatibility functions...")
    waypoints = [(38.5831, -90.4068)]
    osm_link = create_osm_route_link(waypoints)
    gmaps_link = create_google_maps_link(waypoints)
    assert osm_link == osm.create_route_link(waypoints)
    assert gmaps_link == gmaps.create_route_link(waypoints)
    print("✓ Backward compatibility functions work")
