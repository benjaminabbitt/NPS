"""
Unit tests for VRP Trip Planner components

Tests cover:
- Pure functions (haversine, distance/time matrices, map links)
- Site class behavior
- Day budget calculation
- Operating hours constraints
- Optimal start time calculation

Following TDD approach - these tests exercise boundaries and edge cases.
"""
import pytest
import math
from unittest.mock import Mock, patch
from vrp_trip_planner import (
    Site,
    VRPTripPlanner,
    create_osm_route_link,
    create_google_maps_link,
    create_geojson_route,
    calculate_default_max_distance,
    DEFAULT_HOME_LAT,
    DEFAULT_HOME_LON,
    DEFAULT_HOME_NAME,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def home_base():
    """Standard home base (Kirkwood, MO)"""
    return (DEFAULT_HOME_NAME, DEFAULT_HOME_LAT, DEFAULT_HOME_LON)


@pytest.fixture
def sample_sites():
    """Sample NPS sites for testing"""
    return [
        Site(
            name="Gateway Arch NP",
            lat=38.6247,
            lon=-90.1848,
            city="St. Louis",
            state="MO",
        ),
        Site(
            name="Mammoth Cave NP",
            lat=37.1870,
            lon=-86.1008,
            city="Mammoth Cave",
            state="KY",
        ),
        Site(
            name="Indiana Dunes NP",
            lat=41.6533,
            lon=-87.0524,
            city="Porter",
            state="IN",
        ),
    ]


@pytest.fixture
def planner_minimal(home_base, sample_sites):
    """Minimal VRP planner for unit testing"""
    return VRPTripPlanner(
        sites=sample_sites,
        home_base=home_base,
        verbose=False,
    )


# =============================================================================
# Test: Site Class
# =============================================================================

class TestSite:
    """Tests for Site dataclass"""

    def test_site_basic_creation(self):
        site = Site(name="Test Park", lat=38.5, lon=-90.5)
        assert site.name == "Test Park"
        assert site.lat == 38.5
        assert site.lon == -90.5

    def test_site_full_name_with_city_state(self):
        site = Site(name="Test Park", lat=38.5, lon=-90.5, city="St. Louis", state="MO")
        assert site.full_name == "Test Park, St. Louis, MO"

    def test_site_full_name_without_city_state(self):
        site = Site(name="Test Park", lat=38.5, lon=-90.5)
        assert site.full_name == "Test Park"

    def test_site_default_values(self):
        site = Site(name="Test", lat=0.0, lon=0.0)
        assert site.address == ""
        assert site.city == ""
        assert site.state == ""
        assert site.operating_hours is None
        assert site.always_stamp_available is False

    def test_site_with_operating_hours(self):
        from nps_data_loader import OperatingHours
        hours = OperatingHours(opens=540, closes=1020)  # 9 AM - 5 PM
        site = Site(name="Test", lat=0.0, lon=0.0, operating_hours=hours)
        assert site.operating_hours.opens == 540
        assert site.operating_hours.closes == 1020

    def test_site_always_stamp_available_flag(self):
        site = Site(name="Test", lat=0.0, lon=0.0, always_stamp_available=True)
        assert site.always_stamp_available is True

    def test_site_get_timezone_returns_string(self):
        """Timezone lookup should return a timezone string"""
        site = Site(name="Gateway Arch NP", lat=38.6247, lon=-90.1848)
        tz = site.get_timezone()
        assert isinstance(tz, str)
        assert "America/" in tz  # Should be a US timezone

    def test_site_get_timezone_defaults_to_central(self):
        """Invalid coordinates should default to America/Chicago"""
        site = Site(name="Invalid", lat=0.0, lon=0.0)
        # Ocean location might not have timezone, should default
        tz = site.get_timezone()
        assert isinstance(tz, str)


# =============================================================================
# Test: Default Max Distance Calculation
# =============================================================================

class TestDefaultMaxDistance:
    """Tests for calculate_default_max_distance function"""

    def test_three_day_trip(self):
        """3 days × 10 hours × 55 mph × 0.4 = 660 miles"""
        result = calculate_default_max_distance(3)
        assert result == 660

    def test_seven_day_trip(self):
        """7 days × 10 hours × 55 mph × 0.4 = 1540 miles"""
        result = calculate_default_max_distance(7)
        assert result == 1540

    def test_fourteen_day_trip(self):
        """14 days × 10 hours × 55 mph × 0.4 = 3080 miles"""
        result = calculate_default_max_distance(14)
        assert result == 3080

    def test_one_day_trip(self):
        """1 day × 10 hours × 55 mph × 0.4 = 220 miles"""
        result = calculate_default_max_distance(1)
        assert result == 220

    def test_returns_integer(self):
        """Result should be an integer"""
        result = calculate_default_max_distance(5)
        assert isinstance(result, int)


# =============================================================================
# Test: Map Link Generation
# =============================================================================

class TestMapLinks:
    """Tests for map link generation functions"""

    def test_osm_link_single_waypoint(self):
        waypoints = [(38.5831, -90.4068)]
        link = create_osm_route_link(waypoints)
        assert "openstreetmap.org/directions" in link
        assert "38.5831,-90.4068" in link

    def test_osm_link_multiple_waypoints(self):
        waypoints = [
            (38.5831, -90.4068),  # Kirkwood
            (38.6247, -90.1848),  # Gateway Arch
            (37.187, -86.1008),   # Mammoth Cave
        ]
        link = create_osm_route_link(waypoints)
        assert "38.5831,-90.4068" in link
        assert "38.6247,-90.1848" in link
        assert "37.187,-86.1008" in link
        assert ";" in link  # Waypoints separated by semicolons

    def test_osm_link_uses_fossgis_engine(self):
        waypoints = [(38.5831, -90.4068), (38.6247, -90.1848)]
        link = create_osm_route_link(waypoints)
        assert "fossgis_osrm_car" in link

    def test_google_maps_link_empty_returns_empty(self):
        link = create_google_maps_link([])
        assert link == ""

    def test_google_maps_link_single_point(self):
        waypoints = [(38.5831, -90.4068)]
        link = create_google_maps_link(waypoints)
        assert "google.com/maps/dir" in link
        assert "38.5831,-90.4068" in link

    def test_google_maps_link_multiple_waypoints(self):
        waypoints = [
            (38.5831, -90.4068),  # Start
            (38.6247, -90.1848),  # Middle
            (37.187, -86.1008),   # End
        ]
        link = create_google_maps_link(waypoints)
        assert "google.com/maps/dir" in link
        # All waypoints should appear in order
        assert "38.5831,-90.4068" in link
        assert "38.6247,-90.1848" in link
        assert "37.187,-86.1008" in link


# =============================================================================
# Test: GeoJSON Generation
# =============================================================================

class TestGeoJSONGeneration:
    """Tests for create_geojson_route function"""

    def test_geojson_structure(self):
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'Start', 'lat': 38.58, 'lon': -90.40, 'day': 1, 'time_of_day': '09:00'},
                {'site': 'End', 'lat': 38.62, 'lon': -90.18, 'day': 1, 'time_of_day': '11:00'},
            ],
            'stats': {
                'total_sites': 1,
                'total_distance_miles': 10.5,
                'total_days': 1,
            }
        }
        geojson = create_geojson_route(trip_data)

        assert geojson['type'] == 'FeatureCollection'
        assert 'features' in geojson
        assert len(geojson['features']) >= 1

    def test_geojson_has_linestring(self):
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'A', 'lat': 38.58, 'lon': -90.40, 'day': 1, 'time_of_day': '09:00'},
                {'site': 'B', 'lat': 38.62, 'lon': -90.18, 'day': 1, 'time_of_day': '11:00'},
            ],
            'stats': {'total_sites': 1, 'total_distance_miles': 10, 'total_days': 1}
        }
        geojson = create_geojson_route(trip_data)

        # First feature should be LineString
        linestring_feature = geojson['features'][0]
        assert linestring_feature['geometry']['type'] == 'LineString'
        assert len(linestring_feature['geometry']['coordinates']) == 2

    def test_geojson_coordinates_in_lon_lat_order(self):
        """GeoJSON uses [lon, lat] not [lat, lon]"""
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'A', 'lat': 38.58, 'lon': -90.40, 'day': 1, 'time_of_day': '09:00'},
            ],
            'stats': {'total_sites': 1, 'total_distance_miles': 10, 'total_days': 1}
        }
        geojson = create_geojson_route(trip_data)

        coords = geojson['features'][0]['geometry']['coordinates']
        # First coordinate should be lon (-90.40), second lat (38.58)
        assert coords[0][0] == -90.40
        assert coords[0][1] == 38.58

    def test_geojson_has_point_features(self):
        trip_data = {
            'trip_number': 1,
            'route_details': [
                {'site': 'A', 'lat': 38.58, 'lon': -90.40, 'day': 1, 'time_of_day': '09:00'},
                {'site': 'B', 'lat': 38.62, 'lon': -90.18, 'day': 1, 'time_of_day': '11:00'},
            ],
            'stats': {'total_sites': 1, 'total_distance_miles': 10, 'total_days': 1}
        }
        geojson = create_geojson_route(trip_data)

        # Should have LineString + 2 Point features
        point_features = [f for f in geojson['features'] if f['geometry']['type'] == 'Point']
        assert len(point_features) == 2


# =============================================================================
# Test: Haversine Distance Calculation
# =============================================================================

class TestHaversineDistance:
    """Tests for VRPTripPlanner._haversine_distance method"""

    def test_same_point_returns_zero(self, planner_minimal):
        dist = planner_minimal._haversine_distance(38.5, -90.4, 38.5, -90.4)
        assert dist == 0.0

    def test_kirkwood_to_gateway_arch(self, planner_minimal):
        """Known distance: Kirkwood to Gateway Arch ~12-15 miles"""
        dist = planner_minimal._haversine_distance(
            38.5831, -90.4068,  # Kirkwood
            38.6247, -90.1848   # Gateway Arch
        )
        assert 10 < dist < 18  # Roughly 12-15 miles (haversine)

    def test_kirkwood_to_mammoth_cave(self, planner_minimal):
        """Known distance: Kirkwood to Mammoth Cave ~250 miles"""
        dist = planner_minimal._haversine_distance(
            38.5831, -90.4068,  # Kirkwood
            37.1870, -86.1008   # Mammoth Cave
        )
        assert 230 < dist < 280  # Roughly 250 miles

    def test_returns_miles_not_km(self, planner_minimal):
        """Verify Earth radius is for miles (3959), not km (6371)"""
        # NYC to LA is ~2,450 miles
        dist = planner_minimal._haversine_distance(
            40.7128, -74.0060,  # NYC
            34.0522, -118.2437  # LA
        )
        assert 2400 < dist < 2500  # In miles, not km (~3900)


# =============================================================================
# Test: Distance Matrix Creation
# =============================================================================

class TestDistanceMatrix:
    """Tests for VRPTripPlanner._create_distance_matrix method"""

    def test_matrix_has_correct_dimensions(self, planner_minimal):
        matrix = planner_minimal._create_distance_matrix()
        n = len(planner_minimal.sites)  # Includes home base
        assert len(matrix) == n
        assert all(len(row) == n for row in matrix)

    def test_diagonal_is_zero(self, planner_minimal):
        matrix = planner_minimal._create_distance_matrix()
        for i in range(len(matrix)):
            assert matrix[i][i] == 0

    def test_matrix_is_symmetric(self, planner_minimal):
        matrix = planner_minimal._create_distance_matrix()
        n = len(matrix)
        for i in range(n):
            for j in range(n):
                assert matrix[i][j] == matrix[j][i]

    def test_matrix_values_in_meters(self, planner_minimal):
        """Matrix should store distances in meters for OR-Tools"""
        matrix = planner_minimal._create_distance_matrix()
        # Distance from Kirkwood (index 0) to Gateway Arch (index 1) ~15 miles
        # 15 miles * 1609.34 = ~24,000 meters
        # Gateway Arch is first site after home base (index 1)
        dist_meters = matrix[0][1]
        dist_miles = dist_meters / 1609.34
        assert 10 < dist_miles < 20  # Roughly 15 miles


# =============================================================================
# Test: Time Matrix Creation
# =============================================================================

class TestTimeMatrix:
    """Tests for VRPTripPlanner._create_time_matrix method"""

    def test_matrix_has_correct_dimensions(self, planner_minimal):
        distance_matrix = planner_minimal._create_distance_matrix()
        time_matrix = planner_minimal._create_time_matrix(distance_matrix)
        n = len(planner_minimal.sites)
        assert len(time_matrix) == n
        assert all(len(row) == n for row in time_matrix)

    def test_diagonal_is_zero(self, planner_minimal):
        distance_matrix = planner_minimal._create_distance_matrix()
        time_matrix = planner_minimal._create_time_matrix(distance_matrix)
        for i in range(len(time_matrix)):
            assert time_matrix[i][i] == 0

    def test_time_includes_visit_time(self, planner_minimal):
        """Time to site should include drive time + visit time"""
        distance_matrix = planner_minimal._create_distance_matrix()
        time_matrix = planner_minimal._create_time_matrix(distance_matrix)

        # Time from depot to first site should be drive time + visit time
        # Gateway Arch is ~15 miles from Kirkwood at 55mph = ~16 min drive
        # Plus 2 hours (120 min) visit = ~136 min total
        time_to_site = time_matrix[0][1]
        assert time_to_site > 100  # At least 100 minutes (drive + visit)

    def test_time_to_depot_excludes_visit(self, planner_minimal):
        """Returning to depot should not add visit time"""
        distance_matrix = planner_minimal._create_distance_matrix()
        time_matrix = planner_minimal._create_time_matrix(distance_matrix)

        # Time from first site back to depot should be only drive time
        time_back_to_depot = time_matrix[1][0]  # Gateway Arch to Kirkwood
        dist_miles = distance_matrix[1][0] / 1609.34
        expected_drive_min = (dist_miles / planner_minimal.avg_speed_mph) * 60

        # Should be just drive time (no visit time added)
        assert abs(time_back_to_depot - expected_drive_min) < 2  # Within 2 minutes


# =============================================================================
# Test: Day Budget Checking
# =============================================================================

class TestDayBudgetChecking:
    """Tests for VRPTripPlanner._check_site_fits_in_day method"""

    def test_empty_day_site_fits(self, planner_minimal):
        new_site = {
            'lat': 38.6247,
            'lon': -90.1848,
            'site_name': 'Gateway Arch'
        }
        fits, arrival_time = planner_minimal._check_site_fits_in_day(
            sites_in_day=[],
            new_site=new_site,
            start_location=(38.5831, -90.4068),
            day_budget_minutes=18 * 60,  # 18 hours
            start_hour=6
        )
        assert fits is True
        assert arrival_time >= 0

    def test_site_exceeds_budget_returns_false(self, planner_minimal):
        """Site that would exceed day budget should not fit"""
        new_site = {
            'lat': 41.6533,  # Indiana Dunes - far away
            'lon': -87.0524,
            'site_name': 'Indiana Dunes'
        }
        # With only 2 hours budget, can't reach Indiana Dunes from Kirkwood
        fits, arrival_time = planner_minimal._check_site_fits_in_day(
            sites_in_day=[],
            new_site=new_site,
            start_location=(38.5831, -90.4068),
            day_budget_minutes=120,  # Only 2 hours
            start_hour=6
        )
        assert fits is False

    def test_accumulates_time_for_existing_sites(self, planner_minimal):
        """Time should accumulate from sites already in day"""
        existing_sites = [
            {'lat': 38.6247, 'lon': -90.1848, 'site_name': 'Gateway Arch'}
        ]
        new_site = {
            'lat': 37.1870,  # Mammoth Cave
            'lon': -86.1008,
            'site_name': 'Mammoth Cave'
        }

        # With 6 hours, shouldn't fit after visiting Gateway Arch
        fits, arrival_time = planner_minimal._check_site_fits_in_day(
            sites_in_day=existing_sites,
            new_site=new_site,
            start_location=(38.5831, -90.4068),
            day_budget_minutes=6 * 60,  # 6 hours
            start_hour=6
        )
        assert fits is False


# =============================================================================
# Test: Optimal Start Time Calculation
# =============================================================================

class TestOptimalStartTime:
    """Tests for VRPTripPlanner._calculate_optimal_start_hour method"""

    def test_empty_route_returns_preferred_hour(self, planner_minimal):
        """Route with only depot should return preferred start (9 AM)"""
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068, 'site_name': 'Kirkwood, MO'}
        ]
        start_hour = planner_minimal._calculate_optimal_start_hour(route_details)
        assert start_hour == planner_minimal.preferred_start_hour

    def test_site_without_hours_returns_preferred(self, planner_minimal):
        """Site without operating hours should use preferred start"""
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068, 'site_name': 'Kirkwood, MO'},
            {'lat': 38.6247, 'lon': -90.1848, 'site_name': 'Gateway Arch'},
        ]
        start_hour = planner_minimal._calculate_optimal_start_hour(route_details)
        assert start_hour == planner_minimal.preferred_start_hour

    def test_site_opens_late_uses_preferred(self, planner_minimal):
        """If site opens late enough, use preferred start time"""
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068, 'site_name': 'Kirkwood'},
            {
                'lat': 38.6247, 'lon': -90.1848, 'site_name': 'Late Site',
                'operating_hours': {'opens': 10 * 60}  # Opens 10 AM
            },
        ]
        start_hour = planner_minimal._calculate_optimal_start_hour(route_details)
        # Travel time is ~16 min, so starting at 9am arrives well before 10am opening
        # Should still use preferred start
        assert start_hour == planner_minimal.preferred_start_hour

    def test_never_starts_before_earliest(self, planner_minimal):
        """Should never start before earliest allowed (6 AM)"""
        route_details = [
            {'lat': 38.5831, 'lon': -90.4068, 'site_name': 'Kirkwood'},
            {
                'lat': 38.6247, 'lon': -90.1848, 'site_name': 'Early Site',
                'operating_hours': {'opens': 5 * 60}  # Opens 5 AM (before allowed)
            },
        ]
        start_hour = planner_minimal._calculate_optimal_start_hour(route_details)
        assert start_hour >= planner_minimal.earliest_start_hour


# =============================================================================
# Test: VRP Planner Configuration
# =============================================================================

class TestVRPPlannerConfig:
    """Tests for VRPTripPlanner configuration and initialization"""

    def test_home_base_added_as_depot(self, home_base, sample_sites):
        planner = VRPTripPlanner(sites=sample_sites, home_base=home_base)
        # Sites list should include home base as first element
        assert len(planner.sites) == len(sample_sites) + 1
        assert planner.sites[0].name == DEFAULT_HOME_NAME

    def test_default_visit_time_is_two_hours(self, home_base, sample_sites):
        planner = VRPTripPlanner(sites=sample_sites, home_base=home_base)
        assert planner.visit_minutes_per_site == 120  # 2 hours

    def test_custom_visit_time(self, home_base, sample_sites):
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=home_base,
            visit_hours_per_site=3.0
        )
        assert planner.visit_minutes_per_site == 180  # 3 hours

    def test_default_hours_per_day(self, home_base, sample_sites):
        planner = VRPTripPlanner(sites=sample_sites, home_base=home_base)
        assert planner.hours_per_day == 18  # 6am to midnight

    def test_default_preferred_hours_per_day(self, home_base, sample_sites):
        planner = VRPTripPlanner(sites=sample_sites, home_base=home_base)
        assert planner.preferred_hours_per_day == 12

    def test_num_trips_override(self, home_base, sample_sites):
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=home_base,
            num_trips_override=5
        )
        assert planner.num_vehicles == 5

    def test_num_trips_capped_at_30(self, home_base, sample_sites):
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=home_base,
            num_trips_override=50
        )
        assert planner.num_vehicles == 30

    def test_min_sites_per_day_config(self, home_base, sample_sites):
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=home_base,
            min_sites_per_day=1.5
        )
        assert planner.min_sites_per_day == 1.5

    def test_max_sites_per_day_config(self, home_base, sample_sites):
        planner = VRPTripPlanner(
            sites=sample_sites,
            home_base=home_base,
            max_sites_per_day=3.0
        )
        assert planner.max_sites_per_day == 3.0


# =============================================================================
# Test: Constants and Defaults
# =============================================================================

class TestConstants:
    """Tests for module-level constants"""

    def test_default_home_lat(self):
        assert DEFAULT_HOME_LAT == 38.5831

    def test_default_home_lon(self):
        assert DEFAULT_HOME_LON == -90.4068

    def test_default_home_name(self):
        assert DEFAULT_HOME_NAME == "Kirkwood, MO"
