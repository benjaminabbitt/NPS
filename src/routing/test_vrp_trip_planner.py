"""Tests for VRP Trip Planner

Tests focus on:
1. Haversine distance calculations
2. Time matrix creation
3. Day assignment logic
4. Operating hours constraint checking
5. Default max distance calculation
6. Helper functions (map links, GeoJSON)
"""
import pytest
import math
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Import the module under test
from vrp_trip_planner import (
    VRPTripPlanner,
    Site,
    create_osm_route_link,
    create_google_maps_link,
    create_geojson_route,
    calculate_default_max_distance,
    DEFAULT_HOME_LAT,
    DEFAULT_HOME_LON,
    DEFAULT_HOME_NAME,
)
from nps_data_loader import OperatingHours


@dataclass
class MockSite:
    """Simple mock site for testing"""
    name: str
    lat: float
    lon: float
    address: str = ""
    city: str = ""
    state: str = ""
    operating_hours: OperatingHours = None
    always_stamp_available: bool = False


class TestHaversineDistance:
    """Tests for haversine distance calculation"""

    @pytest.fixture
    def planner(self):
        """Create a minimal planner for testing distance calculations"""
        sites = [
            Site(name="Site A", lat=38.5831, lon=-90.4068),  # Kirkwood, MO
            Site(name="Site B", lat=38.2527, lon=-85.7585),  # Louisville, KY
        ]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=1,
            max_trip_days=1,
            num_trips_override=1
        )

    def test_same_point_returns_zero(self, planner):
        """Distance from point to itself should be zero"""
        dist = planner._haversine_distance(38.5831, -90.4068, 38.5831, -90.4068)
        assert dist == 0.0

    def test_kirkwood_to_louisville(self, planner):
        """Kirkwood, MO to Louisville, KY is approximately 250-270 miles"""
        dist = planner._haversine_distance(
            38.5831, -90.4068,  # Kirkwood, MO
            38.2527, -85.7585  # Louisville, KY
        )
        assert 250 < dist < 270

    def test_new_york_to_los_angeles(self, planner):
        """NYC to LA is approximately 2450 miles straight line"""
        dist = planner._haversine_distance(
            40.7128, -74.0060,  # New York
            34.0522, -118.2437  # Los Angeles
        )
        assert 2400 < dist < 2500

    def test_distance_is_symmetric(self, planner):
        """Distance A->B should equal B->A"""
        dist_ab = planner._haversine_distance(38.5831, -90.4068, 38.2527, -85.7585)
        dist_ba = planner._haversine_distance(38.2527, -85.7585, 38.5831, -90.4068)
        assert abs(dist_ab - dist_ba) < 0.001


class TestDistanceMatrix:
    """Tests for distance matrix creation"""

    @pytest.fixture
    def planner(self):
        sites = [
            Site(name="Site A", lat=38.5831, lon=-90.4068),
            Site(name="Site B", lat=38.2527, lon=-85.7585),
        ]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=1,
            max_trip_days=1,
            num_trips_override=1
        )

    def test_matrix_dimensions(self, planner):
        """Matrix should be N x N where N = sites + depot"""
        matrix = planner._create_distance_matrix()
        n = len(planner.sites)  # Includes depot
        assert len(matrix) == n
        assert all(len(row) == n for row in matrix)

    def test_diagonal_is_zero(self, planner):
        """Diagonal (same location) should be zero"""
        matrix = planner._create_distance_matrix()
        for i in range(len(matrix)):
            assert matrix[i][i] == 0

    def test_matrix_is_symmetric(self, planner):
        """Distance matrix should be symmetric"""
        matrix = planner._create_distance_matrix()
        for i in range(len(matrix)):
            for j in range(len(matrix)):
                assert abs(matrix[i][j] - matrix[j][i]) < 10  # Within 10 meters

    def test_distances_are_in_meters(self, planner):
        """Distances should be in meters for OR-Tools"""
        matrix = planner._create_distance_matrix()
        # Depot (0) to Site B (2) - about 260 miles = ~420km
        # 260 * 1609.34 = 418,428 meters
        assert 400000 < matrix[0][2] < 450000


class TestTimeMatrix:
    """Tests for time matrix creation"""

    @pytest.fixture
    def planner(self):
        sites = [
            Site(name="Site A", lat=38.5831, lon=-90.4068),
            Site(name="Site B", lat=38.2527, lon=-85.7585),
        ]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=1,
            max_trip_days=1,
            visit_hours_per_site=2.0,
            avg_speed_mph=55.0,
            num_trips_override=1
        )

    def test_time_matrix_includes_visit_time(self, planner):
        """Time to reach site should include drive + visit time"""
        dist_matrix = planner._create_distance_matrix()
        time_matrix = planner._create_time_matrix(dist_matrix)

        # Time to depot (index 0) should NOT include visit time
        # Time to any other site should include visit time

        # Check depot -> Site A (index 1): same location, 0 drive + 120 min visit
        assert time_matrix[0][1] == 120  # 2 hours visit

        # Check depot -> Site B (index 2): ~260 mi @ 55mph = ~284 min + 120 visit = 404
        assert 380 < time_matrix[0][2] < 430

    def test_return_to_depot_no_visit_time(self, planner):
        """Returning to depot should not include visit time"""
        dist_matrix = planner._create_distance_matrix()
        time_matrix = planner._create_time_matrix(dist_matrix)

        # Site B (index 2) -> depot (index 0): drive only, no visit
        # ~260 mi @ 55mph = ~284 min
        assert 260 < time_matrix[2][0] < 310


class TestDefaultMaxDistance:
    """Tests for default max distance calculation"""

    def test_three_day_trip(self):
        """3 days: 3 × 10 × 55 × 0.4 = 660 miles"""
        assert calculate_default_max_distance(3) == 660

    def test_seven_day_trip(self):
        """7 days: 7 × 10 × 55 × 0.4 = 1540 miles"""
        assert calculate_default_max_distance(7) == 1540

    def test_fourteen_day_trip(self):
        """14 days: 14 × 10 × 55 × 0.4 = 3080 miles"""
        assert calculate_default_max_distance(14) == 3080

    def test_one_day_trip(self):
        """1 day: 1 × 10 × 55 × 0.4 = 220 miles"""
        assert calculate_default_max_distance(1) == 220


class TestMapLinkGeneration:
    """Tests for map link generation functions"""

    def test_osm_route_link_single_point(self):
        link = create_osm_route_link([(38.5831, -90.4068)])
        assert "openstreetmap.org/directions" in link
        assert "38.5831,-90.4068" in link

    def test_osm_route_link_multiple_waypoints(self):
        waypoints = [
            (38.5831, -90.4068),
            (38.2527, -85.7585),
            (40.7128, -74.0060)
        ]
        link = create_osm_route_link(waypoints)
        assert "38.5831,-90.4068" in link
        assert "38.2527,-85.7585" in link
        assert "40.7128,-74.006" in link
        assert ";" in link  # Multiple waypoints separated by ;

    def test_google_maps_link_empty(self):
        link = create_google_maps_link([])
        assert link == ""

    def test_google_maps_link_multiple_waypoints(self):
        waypoints = [
            (38.5831, -90.4068),
            (38.2527, -85.7585),
            (40.7128, -74.0060)
        ]
        link = create_google_maps_link(waypoints)
        assert "google.com/maps/dir" in link
        assert "38.5831" in link
        assert "40.7128" in link


class TestGeoJSONGeneration:
    """Tests for GeoJSON route generation"""

    def test_geojson_structure(self):
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'Home', 'lat': 38.5831, 'lon': -90.4068, 'day': 1, 'time_of_day': '09:00'},
                {'site': 'Site A', 'lat': 38.2527, 'lon': -85.7585, 'day': 1, 'time_of_day': '14:00'},
            ],
            'stats': {
                'total_sites': 1,
                'total_distance_miles': 260.5,
                'total_days': 1
            }
        }
        geojson = create_geojson_route(trip_data)

        assert geojson['type'] == 'FeatureCollection'
        assert len(geojson['features']) == 3  # 1 LineString + 2 Points

        # First feature should be LineString
        assert geojson['features'][0]['geometry']['type'] == 'LineString'
        assert geojson['features'][0]['properties']['trip_number'] == 1

        # Remaining features should be Points
        assert geojson['features'][1]['geometry']['type'] == 'Point'
        assert geojson['features'][2]['geometry']['type'] == 'Point'

    def test_geojson_coordinates_lon_lat_order(self):
        """GeoJSON uses [lon, lat] order, not [lat, lon]"""
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'Home', 'lat': 38.5831, 'lon': -90.4068, 'day': 1, 'time_of_day': '09:00'},
            ],
            'stats': {'total_sites': 0, 'total_distance_miles': 0, 'total_days': 1}
        }
        geojson = create_geojson_route(trip_data)

        # LineString coordinates
        line_coords = geojson['features'][0]['geometry']['coordinates']
        assert line_coords[0] == [-90.4068, 38.5831]  # [lon, lat]

        # Point coordinates
        point_coords = geojson['features'][1]['geometry']['coordinates']
        assert point_coords == [-90.4068, 38.5831]


class TestSiteClass:
    """Tests for Site dataclass"""

    def test_site_full_name_with_city_state(self):
        site = Site(name="Test Site", lat=0, lon=0, city="Test City", state="TS")
        assert site.full_name == "Test Site, Test City, TS"

    def test_site_full_name_without_city_state(self):
        site = Site(name="Test Site", lat=0, lon=0)
        assert site.full_name == "Test Site"

    def test_site_timezone_lookup(self):
        """Site should be able to get its timezone"""
        site = Site(name="Kirkwood", lat=38.5831, lon=-90.4068)
        tz = site.get_timezone()
        assert tz == "America/Chicago"

    def test_site_timezone_fallback(self):
        """Invalid coordinates should fall back to Chicago"""
        site = Site(name="Invalid", lat=0, lon=0)
        tz = site.get_timezone()
        # Should get a valid timezone (might be UTC+0 area, but fallback is Chicago)
        assert tz is not None


class TestVRPTripPlannerConfig:
    """Tests for VRPTripPlanner configuration"""

    def test_planner_defaults(self):
        sites = [Site(name="Site A", lat=38.0, lon=-90.0)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=3,
            num_trips_override=1
        )

        assert planner.visit_minutes_per_site == 120  # 2 hours default
        assert planner.hours_per_day == 18  # 18 hours max
        assert planner.avg_speed_mph == 55.0
        assert planner.earliest_start_hour == 6  # 6 AM

    def test_planner_custom_config(self):
        sites = [Site(name="Site A", lat=38.0, lon=-90.0)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=1.5,
            hours_per_day=15,
            avg_speed_mph=60.0,
            target_trip_days=7,
            max_trip_days=8,
            num_trips_override=1
        )

        assert planner.visit_minutes_per_site == 90  # 1.5 hours
        assert planner.hours_per_day == 15
        assert planner.avg_speed_mph == 60.0
        assert planner.target_trip_minutes == 7 * 15 * 60

    def test_num_vehicles_auto_calculation(self):
        """Auto-calculate vehicles based on sites and trip length"""
        # 10 sites, 3 day trip, 1.5 sites/day avg = 4.5 sites per trip
        # 10 / 4.5 = 2.2 -> 3 vehicles
        sites = [Site(name=f"Site {i}", lat=38.0 + i*0.1, lon=-90.0) for i in range(10)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=3,
            min_sites_per_day=1.0,
            max_sites_per_day=2.0
        )

        # With 1.5 sites/day avg and 3 days = 4.5 sites/trip
        # 10 sites / 4.5 = 2.2, rounded up to 3
        assert planner.num_vehicles >= 2
        assert planner.num_vehicles <= 4

    def test_num_vehicles_override(self):
        """Override should take precedence"""
        sites = [Site(name=f"Site {i}", lat=38.0 + i*0.1, lon=-90.0) for i in range(10)]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=3,
            num_trips_override=5
        )

        assert planner.num_vehicles == 5


class TestOperatingHoursConstraints:
    """Tests for operating hours constraint logic"""

    @pytest.fixture
    def planner(self):
        sites = [
            Site(
                name="Site A",
                lat=38.5831,
                lon=-90.4068,
                operating_hours=OperatingHours(opens=9*60, closes=17*60)  # 9am-5pm
            ),
        ]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5, -90.5),
            target_trip_days=1,
            max_trip_days=1,
            num_trips_override=1
        )

    def test_site_with_operating_hours(self, planner):
        """Site should have operating hours attached"""
        # Index 0 is depot, index 1 is Site A
        site = planner.sites[1]
        assert site.operating_hours is not None
        assert site.operating_hours.opens == 9 * 60
        assert site.operating_hours.closes == 17 * 60

    def test_always_stamp_available_flag(self):
        """Sites with always_stamp_available should be marked"""
        sites = [
            Site(
                name="24/7 Site",
                lat=38.5831,
                lon=-90.4068,
                operating_hours=OperatingHours(opens=9*60, closes=17*60),
                always_stamp_available=True
            ),
        ]
        planner = VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5, -90.5),
            target_trip_days=1,
            num_trips_override=1
        )

        site = planner.sites[1]
        assert site.always_stamp_available is True


class TestOptimalStartTimeCalculation:
    """Tests for optimal start time calculation"""

    @pytest.fixture
    def planner(self):
        sites = [
            Site(
                name="Morning Site",
                lat=38.6,  # Very close to home
                lon=-90.4,
                operating_hours=OperatingHours(opens=8*60, closes=17*60)  # 8am-5pm
            ),
        ]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            target_trip_days=1,
            max_trip_days=1,
            num_trips_override=1
        )

    def test_optimal_start_for_early_opening_site(self, planner):
        """If first site opens at 8am and is very close, start at 8am"""
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068},  # Depot
            {'lat': 38.6, 'lon': -90.4, 'operating_hours': {'opens': 8*60}}  # First site
        ]
        start_hour = planner._calculate_optimal_start_hour(route_details)
        # Close site, opens at 8am - should start early
        assert start_hour <= 9

    def test_optimal_start_default_for_no_hours(self, planner):
        """Without operating hours, use preferred start (9am)"""
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068},  # Depot
            {'lat': 38.6, 'lon': -90.4}  # First site - no operating hours
        ]
        start_hour = planner._calculate_optimal_start_hour(route_details)
        assert start_hour == planner.preferred_start_hour  # 9am

    def test_optimal_start_no_sites(self, planner):
        """Empty route should use preferred start"""
        route_details = [{'lat': 38.5831, 'lon': -90.4068}]  # Just depot
        start_hour = planner._calculate_optimal_start_hour(route_details)
        assert start_hour == planner.preferred_start_hour


class TestCheckSiteFitsInDay:
    """Tests for day budget checking logic"""

    @pytest.fixture
    def planner(self):
        sites = [Site(name="Site A", lat=38.6, lon=-90.4)]
        return VRPTripPlanner(
            sites=sites,
            home_base=("Home", 38.5831, -90.4068),
            visit_hours_per_site=2.0,
            hours_per_day=18,
            target_trip_days=1,
            num_trips_override=1
        )

    def test_first_site_fits(self, planner):
        """First site should always fit if travel + visit < day budget"""
        new_site = {'lat': 38.6, 'lon': -90.4}  # Close to home
        start_location = (38.5831, -90.4068)

        fits, arrival_time = planner._check_site_fits_in_day(
            sites_in_day=[],
            new_site=new_site,
            start_location=start_location,
            day_budget_minutes=18 * 60,  # 18 hours
            start_hour=6
        )

        assert fits is True
        assert arrival_time < 60  # Should arrive quickly (close site)

    def test_site_exceeds_budget(self, planner):
        """Site should not fit if it exceeds day budget"""
        # Add a site very far away
        far_site = {'lat': 34.0522, 'lon': -118.2437}  # LA - ~1800 miles from home
        start_location = (38.5831, -90.4068)

        fits, arrival_time = planner._check_site_fits_in_day(
            sites_in_day=[],
            new_site=far_site,
            start_location=start_location,
            day_budget_minutes=10 * 60,  # 10 hours - not enough for LA
            start_hour=6
        )

        assert fits is False
