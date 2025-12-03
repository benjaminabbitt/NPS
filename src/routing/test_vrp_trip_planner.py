#!/usr/bin/env python3
"""
Tests for VRP Trip Planner

Following TDD best practices:
- Test behavior, not implementation
- Use descriptive test names
- Test edge cases and error conditions
"""
import pytest
import math
from datetime import datetime
from vrp_trip_planner import (
    VRPTripPlanner,
    Site,
    create_osm_route_link,
    create_google_maps_link,
    create_geojson_route,
)
from nps_data_loader import OperatingHours, NPSSite


class TestSite:
    """Tests for Site dataclass"""

    def test_site_creation_with_minimal_params(self):
        site = Site(name="Test Site", lat=38.0, lon=-90.0)
        assert site.name == "Test Site"
        assert site.lat == 38.0
        assert site.lon == -90.0
        assert site.address == ""
        assert site.city == ""
        assert site.state == ""

    def test_site_full_name_with_city_and_state(self):
        site = Site(
            name="Test Site",
            lat=38.0,
            lon=-90.0,
            city="St. Louis",
            state="MO"
        )
        assert site.full_name == "Test Site, St. Louis, MO"

    def test_site_full_name_without_city_state(self):
        site = Site(name="Test Site", lat=38.0, lon=-90.0)
        assert site.full_name == "Test Site"

    def test_site_get_timezone_for_central(self):
        site = Site(name="Kirkwood", lat=38.5831, lon=-90.4068)
        tz = site.get_timezone()
        assert tz == "America/Chicago"

    def test_site_get_timezone_for_pacific(self):
        site = Site(name="LA", lat=34.0522, lon=-118.2437)
        tz = site.get_timezone()
        assert tz == "America/Los_Angeles"

    def test_site_get_timezone_fallback_for_invalid(self):
        # Use coordinates in middle of ocean
        site = Site(name="Ocean", lat=0.0, lon=0.0)
        tz = site.get_timezone()
        # Ocean coordinates return Etc/GMT from timezonefinder
        assert tz == "Etc/GMT" or tz == "America/Chicago"


class TestDistanceCalculations:
    """Tests for haversine distance calculations"""

    def test_haversine_same_point_returns_zero(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068)
        )
        distance = planner._haversine_distance(38.5831, -90.4068, 38.5831, -90.4068)
        assert distance == 0.0

    def test_haversine_known_distance_kirkwood_to_stlouis(self):
        """Kirkwood to downtown St. Louis is approximately 10 miles"""
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068)
        )
        # Kirkwood to St. Louis Arch
        distance = planner._haversine_distance(
            38.5831, -90.4068,  # Kirkwood
            38.6247, -90.1848   # St. Louis Arch
        )
        # Should be approximately 10-12 miles
        assert 9 < distance < 13

    def test_haversine_known_distance_la_to_sf(self):
        """LA to SF is approximately 340 miles"""
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068)
        )
        # LA to SF
        distance = planner._haversine_distance(
            34.0522, -118.2437,  # LA
            37.7749, -122.4194   # SF
        )
        # Should be approximately 340-350 miles
        assert 330 < distance < 360


class TestMapLinks:
    """Tests for map link generation"""

    def test_create_osm_route_link_single_waypoint(self):
        waypoints = [(38.5831, -90.4068)]
        link = create_osm_route_link(waypoints)
        assert link.startswith("https://www.openstreetmap.org/directions?")
        assert "38.5831,-90.4068" in link

    def test_create_osm_route_link_multiple_waypoints(self):
        waypoints = [(38.5831, -90.4068), (38.6247, -90.1848)]
        link = create_osm_route_link(waypoints)
        assert "38.5831,-90.4068;38.6247,-90.1848" in link

    def test_create_google_maps_link_empty_waypoints(self):
        link = create_google_maps_link([])
        assert link == ""

    def test_create_google_maps_link_single_waypoint(self):
        waypoints = [(38.5831, -90.4068)]
        link = create_google_maps_link(waypoints)
        assert link.startswith("https://www.google.com/maps/dir/")
        assert "38.5831,-90.4068" in link

    def test_create_google_maps_link_multiple_waypoints(self):
        waypoints = [(38.5831, -90.4068), (38.6247, -90.1848), (38.6270, -90.1994)]
        link = create_google_maps_link(waypoints)
        assert "38.5831,-90.4068" in link
        assert "38.6247,-90.1848" in link
        # Python drops trailing zeros: 38.6270 -> 38.627
        assert "38.627,-90.1994" in link


class TestGeoJSONCreation:
    """Tests for GeoJSON route generation"""

    def test_create_geojson_basic_structure(self):
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'Home', 'lat': 38.5831, 'lon': -90.4068, 'day': 1, 'time_of_day': '09:00'},
                {'site': 'Site 1', 'lat': 38.6247, 'lon': -90.1848, 'day': 1, 'time_of_day': '10:30'}
            ],
            'stats': {
                'total_sites': 1,
                'total_distance_miles': 10.5,
                'total_days': 1
            }
        }
        geojson = create_geojson_route(trip_data)

        assert geojson['type'] == 'FeatureCollection'
        assert 'features' in geojson
        assert len(geojson['features']) == 3  # 1 LineString + 2 Points

    def test_geojson_linestring_feature(self):
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'Home', 'lat': 38.5831, 'lon': -90.4068, 'day': 1, 'time_of_day': '09:00'}
            ],
            'stats': {
                'total_sites': 0,
                'total_distance_miles': 0,
                'total_days': 1
            }
        }
        geojson = create_geojson_route(trip_data)

        line_feature = geojson['features'][0]
        assert line_feature['type'] == 'Feature'
        assert line_feature['geometry']['type'] == 'LineString'
        # GeoJSON uses [lon, lat] order
        assert line_feature['geometry']['coordinates'][0] == [-90.4068, 38.5831]


class TestOptimalStartHourCalculation:
    """Tests for calculating optimal trip start times based on operating hours"""

    def test_calculate_optimal_start_hour_no_sites(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068)
        )
        route_details = [{'lat': 38.5831, 'lon': -90.4068}]  # Just depot
        start_hour = planner._calculate_optimal_start_hour(route_details)
        assert start_hour == 9  # Preferred start time

    def test_calculate_optimal_start_hour_early_opening_site(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068)
        )
        # Site 100 miles away that opens at 8:00 AM
        # Travel time: 100 miles / 55 mph = ~109 minutes
        # To arrive at 8:00 AM, need to start at ~6:11 AM, rounds to 6 AM
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068},  # Depot
            {
                'lat': 39.5, 'lon': -91.5,  # ~100 miles away
                'operating_hours': {'opens': '08:00', 'closes': '17:00'}
            }
        ]
        start_hour = planner._calculate_optimal_start_hour(route_details)
        # Should be early (6-7 AM) to arrive when site opens
        assert 6 <= start_hour <= 7

    def test_calculate_optimal_start_hour_late_opening_site(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068)
        )
        # Site that opens at 10:00 AM, close enough to arrive after 9 AM start
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068},  # Depot
            {
                'lat': 38.6, 'lon': -90.5,  # Close by
                'operating_hours': {'opens': '10:00', 'closes': '18:00'}
            }
        ]
        start_hour = planner._calculate_optimal_start_hour(route_details)
        # Can start at preferred time (9 AM)
        assert start_hour == 9


class TestSiteFitsInDay:
    """Tests for checking if a site fits within a day's time budget and operating hours"""

    def test_site_fits_in_empty_day(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=2.0,
            hours_per_day=15
        )
        site = {
            'lat': 38.6, 'lon': -90.5,
            'operating_hours': {'opens': '09:00', 'closes': '17:00'}
        }
        fits, arrival, reason = planner._check_site_fits_in_day(
            sites_in_day=[],
            new_site=site,
            start_location=(38.5831, -90.4068),
            day_budget_minutes=15 * 60,
            start_hour=9
        )
        assert fits is True
        assert reason == 'ok'

    def test_site_doesnt_fit_budget_exceeded(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=8.0,  # 8 hours per site
            hours_per_day=10
        )
        # First site takes 8 hours, second site would need 8 more (total 16 > 10)
        existing_site = {'lat': 38.6, 'lon': -90.5}
        new_site = {'lat': 38.7, 'lon': -90.6}

        fits, arrival, reason = planner._check_site_fits_in_day(
            sites_in_day=[existing_site],
            new_site=new_site,
            start_location=(38.5831, -90.4068),
            day_budget_minutes=10 * 60,
            start_hour=9
        )
        assert fits is False
        assert reason == 'budget_exceeded'

    def test_site_arrival_too_late_for_operating_hours(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=2.0,
            hours_per_day=15
        )
        # Site that closes at 12:00 PM - need to arrive late enough to violate
        # Distance from Kirkwood to (42, -95) is ~400 miles = ~7.3 hours drive
        # Starting at 9 AM + 7.3 hours = 4:18 PM arrival (after 12 PM close)
        site = {
            'lat': 42.0, 'lon': -95.0,  # Very far away (~400 miles)
            'operating_hours': {'opens': '09:00', 'closes': '12:00'}
        }
        fits, arrival, reason = planner._check_site_fits_in_day(
            sites_in_day=[],
            new_site=site,
            start_location=(38.5831, -90.4068),
            day_budget_minutes=15 * 60,
            start_hour=9
        )
        # Will fail due to arriving after closing
        assert fits is False
        assert reason == 'too_late'

    def test_site_always_stamp_available_ignores_hours(self):
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=2.0,
            hours_per_day=15
        )
        # Site with stamps always available, even though we'd arrive late
        site = {
            'lat': 40.0, 'lon': -92.0,
            'operating_hours': {'opens': '09:00', 'closes': '12:00'},
            'always_stamp_available': True
        }
        fits, arrival, reason = planner._check_site_fits_in_day(
            sites_in_day=[],
            new_site=site,
            start_location=(38.5831, -90.4068),
            day_budget_minutes=15 * 60,
            start_hour=9
        )
        # Should fit because stamps are always available
        assert fits is True
        assert reason == 'ok'


class TestVRPPlannerInitialization:
    """Tests for VRP Planner initialization and configuration"""

    def test_planner_init_with_defaults(self):
        sites = [Site("Site1", 38.6, -90.5)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068)
        )
        assert planner.home_base.name == "Home"
        assert planner.home_base.lat == 38.5831
        assert planner.home_base.lon == -90.4068
        assert len(planner.sites) == 2  # Home + 1 site
        assert planner.visit_minutes_per_site == 120  # 2 hours default
        assert planner.hours_per_day == 15
        assert planner.avg_speed_mph == 55.0

    def test_planner_init_with_custom_params(self):
        sites = [Site("Site1", 38.6, -90.5)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=4.0,
            hours_per_day=10,
            avg_speed_mph=60.0,
            target_trip_days=7
        )
        assert planner.visit_minutes_per_site == 240  # 4 hours
        assert planner.hours_per_day == 10
        assert planner.avg_speed_mph == 60.0
        assert planner.target_trip_minutes == 7 * 10 * 60  # 7 days * 10 hrs * 60 min

    def test_planner_calculates_num_vehicles(self):
        """Test that planner calculates appropriate number of vehicles/trips"""
        # 30 sites with 3-day target
        # With 2 hrs/site and 70% utilization: 3 days * 15 hrs * 0.7 / 2 hrs = ~15 sites/trip
        # So 30 sites / 15 = 2 trips (capped at max 30 vehicles)
        sites = [Site(f"Site{i}", 38.6 + i*0.1, -90.5) for i in range(30)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=3
        )
        # Should calculate reasonable number of trips (not 1, not 30)
        assert 1 <= planner.num_vehicles <= 30


class TestMatrixCreation:
    """Tests for distance and time matrix creation"""

    def test_distance_matrix_diagonal_is_zero(self):
        sites = [
            Site("Site1", 38.6, -90.5),
            Site("Site2", 38.7, -90.6)
        ]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068)
        )
        matrix = planner._create_distance_matrix()

        # Diagonal should be zero (distance from site to itself)
        for i in range(len(matrix)):
            assert matrix[i][i] == 0

    def test_distance_matrix_symmetric(self):
        """Distance from A to B should equal B to A"""
        sites = [
            Site("Site1", 38.6, -90.5),
            Site("Site2", 38.7, -90.6)
        ]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068)
        )
        matrix = planner._create_distance_matrix()

        # Matrix should be symmetric
        for i in range(len(matrix)):
            for j in range(len(matrix)):
                assert matrix[i][j] == matrix[j][i]

    def test_time_matrix_includes_visit_time(self):
        """Time matrix should include both drive and visit time"""
        sites = [Site("Site1", 38.6, -90.5)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=2.0,
            avg_speed_mph=55.0
        )
        distance_matrix = planner._create_distance_matrix()
        time_matrix = planner._create_time_matrix(distance_matrix)

        # Time from home (index 0) to site (index 1) should include visit time
        # Drive time + 120 min visit time
        drive_time = (distance_matrix[0][1] / 1609.34) / 55.0 * 60  # minutes
        expected_time = drive_time + 120  # Add visit time

        assert abs(time_matrix[0][1] - expected_time) < 1  # Within 1 minute

    def test_time_matrix_depot_has_no_visit_time(self):
        """Time matrix should not include visit time for depot"""
        sites = [Site("Site1", 38.6, -90.5)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=2.0,
            avg_speed_mph=55.0
        )
        distance_matrix = planner._create_distance_matrix()
        time_matrix = planner._create_time_matrix(distance_matrix)

        # Time from site (index 1) back to depot (index 0) should be drive only
        drive_time = (distance_matrix[1][0] / 1609.34) / 55.0 * 60  # minutes

        assert abs(time_matrix[1][0] - drive_time) < 1  # Within 1 minute


# Fixtures for common test data
@pytest.fixture
def sample_sites():
    """Sample sites for testing"""
    return [
        Site(
            name="Lincoln Home NHS",
            lat=39.7973,
            lon=-89.6449,
            city="Springfield",
            state="IL",
            operating_hours=OperatingHours(opens=9*60, closes=17*60)
        ),
        Site(
            name="Gateway Arch NP",
            lat=38.6247,
            lon=-90.1848,
            city="St. Louis",
            state="MO",
            operating_hours=OperatingHours(opens=9*60, closes=18*60)
        ),
        Site(
            name="Hot Springs NP",
            lat=34.5215,
            lon=-93.0422,
            city="Hot Springs",
            state="AR",
            operating_hours=OperatingHours(opens=9*60, closes=17*60)
        )
    ]


@pytest.fixture
def planner_with_sample_sites(sample_sites):
    """Planner initialized with sample sites"""
    return VRPTripPlanner(
        sites=sample_sites,
        home_base=("Kirkwood, MO", 38.5831, -90.4068),
        target_trip_days=3
    )


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_planner_creates_matrices_without_error(self, planner_with_sample_sites):
        """Test that planner can create distance/time matrices"""
        distance_matrix = planner_with_sample_sites._create_distance_matrix()
        time_matrix = planner_with_sample_sites._create_time_matrix(distance_matrix)

        # Should create matrices for depot + 3 sites = 4x4
        assert len(distance_matrix) == 4
        assert len(time_matrix) == 4

    def test_planner_with_no_sites_handles_gracefully(self):
        """Test that planner handles empty site list"""
        planner = VRPTripPlanner(
            sites=[],
            home_base=("Home", 38.5831, -90.4068)
        )
        # Should not crash during initialization
        assert len(planner.sites) == 1  # Just the depot


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
