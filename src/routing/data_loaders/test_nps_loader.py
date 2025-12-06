#!/usr/bin/env python3
"""
Tests for NPSSiteLoader
"""
import pytest
from unittest.mock import Mock
from pathlib import Path
from core.site import Site
from .nps_loader import NPSSiteLoader, NPSSiteData
from .types import CancellationStamp, Activity


class TestNPSSiteLoader:
    """Tests for NPSSiteLoader"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        return {
            'file_reader': Mock(),
            'frontmatter_parser': Mock(),
            'markdown_parser': Mock(),
            'duration_parser': Mock()
        }

    @pytest.fixture
    def loader(self, mock_dependencies):
        """Create loader with mocked dependencies"""
        return NPSSiteLoader(**mock_dependencies)

    def test_loader_initialization(self, loader, mock_dependencies):
        """Loader should initialize with injected dependencies"""
        assert loader.file_reader == mock_dependencies['file_reader']
        assert loader.frontmatter_parser == mock_dependencies['frontmatter_parser']
        assert loader.markdown_parser == mock_dependencies['markdown_parser']
        assert loader.duration_parser == mock_dependencies['duration_parser']

    def test_parse_stamps_basic(self, loader):
        """Should parse basic stamp entries"""
        items = [
            '**Visitor Center** (123 Main St; 9:00 AM - 5:00 PM; 555-1234)'
        ]
        stamps = loader._parse_stamps(items)

        assert len(stamps) == 1
        assert stamps[0].location == 'Visitor Center'
        assert stamps[0].address == '123 Main St'
        assert stamps[0].hours == '9:00 AM - 5:00 PM'
        assert stamps[0].phone == '555-1234'

    def test_parse_stamps_with_geocode(self, loader):
        """Should extract geocode from address"""
        items = [
            '**Center** (123 Main St (38.5, -90.4); 9:00 AM - 5:00 PM)'
        ]
        stamps = loader._parse_stamps(items)

        assert len(stamps) == 1
        assert stamps[0].geocode == (38.5, -90.4)

    def test_parse_stamps_html_bold(self, loader):
        """Should handle HTML bold tags"""
        items = [
            '<strong>Visitor Center</strong> (123 Main St; 9:00 AM - 5:00 PM)'
        ]
        stamps = loader._parse_stamps(items)

        assert len(stamps) == 1
        assert stamps[0].location == 'Visitor Center'

    def test_parse_activities_basic(self, loader):
        """Should parse basic activity entries"""
        loader.duration_parser.parse.return_value = 2.0

        items = [
            '**Hiking Trail** (2 hours) - Beautiful scenic trail. [Source: https://example.com]'
        ]
        activities = loader._parse_activities(items)

        assert len(activities) == 1
        assert activities[0].name == 'Hiking Trail'
        assert activities[0].duration_hours == 2.0
        assert activities[0].description == 'Beautiful scenic trail.'
        assert 'https://example.com' in activities[0].sources

    def test_parse_activities_nearby_with_distance(self, loader):
        """Should parse nearby activities with distance"""
        loader.duration_parser.parse.side_effect = [1.5, 1.5]

        items = [
            '**Museum** (1.5 hours, 10 miles) - Interesting exhibits.'
        ]
        activities = loader._parse_activities(items, is_nearby=True)

        assert len(activities) == 1
        assert activities[0].name == 'Museum'
        assert activities[0].distance == '10 miles'

    def test_parse_activities_html_bold(self, loader):
        """Should handle HTML bold tags in activities"""
        loader.duration_parser.parse.return_value = 3.0

        items = [
            '<strong>Tour</strong> (3 hours) - Guided tour.'
        ]
        activities = loader._parse_activities(items)

        assert len(activities) == 1
        assert activities[0].name == 'Tour'

    def test_is_checked_exact_match(self):
        """Should match exact names"""
        assert NPSSiteLoader._is_checked('Visitor Center', ['Visitor Center'])

    def test_is_checked_partial_match(self):
        """Should match partial names"""
        assert NPSSiteLoader._is_checked('Visitor Center', ['Visitor'])
        assert NPSSiteLoader._is_checked('Center', ['Visitor Center'])

    def test_is_checked_case_insensitive(self):
        """Should be case insensitive"""
        assert NPSSiteLoader._is_checked('Visitor Center', ['visitor center'])
        assert NPSSiteLoader._is_checked('VISITOR CENTER', ['visitor center'])

    def test_is_checked_not_found(self):
        """Should return False when not found"""
        assert not NPSSiteLoader._is_checked('Museum', ['Visitor Center', 'Trail'])


class TestNPSSiteLoaderIntegration:
    """Integration tests with mock file system"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies with realistic behavior"""
        file_reader = Mock()
        frontmatter_parser = Mock()
        markdown_parser = Mock()
        duration_parser = Mock()

        # Setup realistic responses
        file_reader.read.return_value = "# Test Site\nContent"
        frontmatter_parser.parse.return_value = ({}, "Content")
        markdown_parser.parse.return_value = {}
        duration_parser.parse.return_value = 2.0

        return {
            'file_reader': file_reader,
            'frontmatter_parser': frontmatter_parser,
            'markdown_parser': markdown_parser,
            'duration_parser': duration_parser
        }

    @pytest.fixture
    def loader(self, mock_dependencies):
        """Create loader with mocked dependencies"""
        return NPSSiteLoader(**mock_dependencies)

    def test_merge_checklist_states_stamps(self):
        """Should merge stamp completion states"""
        main_data = {
            'stamps': [
                CancellationStamp(location='Center A', address='123 Main'),
                CancellationStamp(location='Center B', address='456 Oak')
            ]
        }
        user_checklist = {
            'stamps_checked': ['Center A']
        }

        NPSSiteLoader._merge_checklist_states(main_data, user_checklist)

        assert main_data['stamps'][0].completed is True
        assert main_data['stamps'][1].completed is False

    def test_merge_checklist_states_activities(self):
        """Should merge activity completion states"""
        main_data = {
            'key_activities': [
                Activity(name='Hiking', duration_hours=2.0),
                Activity(name='Biking', duration_hours=1.0)
            ]
        }
        user_checklist = {
            'activities_checked': ['Hiking']
        }

        NPSSiteLoader._merge_checklist_states(main_data, user_checklist)

        assert main_data['key_activities'][0].completed is True
        assert main_data['key_activities'][1].completed is False


class TestNPSSiteLoaderEdgeCases:
    """Edge case tests"""

    @pytest.fixture
    def loader(self):
        """Create loader with mocked dependencies"""
        return NPSSiteLoader(
            file_reader=Mock(),
            frontmatter_parser=Mock(),
            markdown_parser=Mock(),
            duration_parser=Mock()
        )

    def test_parse_stamps_empty_list(self, loader):
        """Should handle empty stamp list"""
        stamps = loader._parse_stamps([])
        assert stamps == []

    def test_parse_stamps_no_match(self, loader):
        """Should handle items that don't match pattern"""
        items = ['Invalid format without bold or parens']
        stamps = loader._parse_stamps(items)
        assert stamps == []

    def test_parse_activities_empty_list(self, loader):
        """Should handle empty activity list"""
        activities = loader._parse_activities([])
        assert activities == []

    def test_parse_activities_no_match(self, loader):
        """Should handle items that don't match pattern"""
        items = ['Invalid format']
        activities = loader._parse_activities(items)
        assert activities == []

    def test_is_checked_empty_list(self):
        """Should handle empty checked list"""
        assert not NPSSiteLoader._is_checked('Item', [])

    def test_merge_checklist_empty_lists(self):
        """Should handle empty lists in merge"""
        main_data = {
            'stamps': [],
            'key_activities': [],
            'hidden_gems': [],
            'also_nearby': []
        }
        user_checklist = {
            'stamps_checked': [],
            'activities_checked': [],
            'gems_checked': [],
            'nearby_checked': []
        }

        # Should not raise exception
        NPSSiteLoader._merge_checklist_states(main_data, user_checklist)
