#!/usr/bin/env python3
"""
Data Loader Factory

Creates data loaders with properly injected dependencies following IoC pattern.
"""
from .nps_loader import NPSSiteLoader
from .attraction_loader import WorldsLargestLoader, AmusementParkLoader
from .unified_loader import UnifiedDataLoader
from .parsers import (
    StandardFileReader,
    StandardFrontmatterParser,
    MistuneMarkdownParser,
    RegexDurationParser,
    RegexOperatingHoursParser
)


class DataLoaderFactory:
    """
    Factory for creating data loaders with proper dependency injection.

    Follows IoC principle: components don't create their own dependencies,
    they receive them from the factory.
    """

    @staticmethod
    def create_nps_loader() -> NPSSiteLoader:  # pragma: no cover
        """Create NPS site loader with real dependencies"""
        return NPSSiteLoader(
            file_reader=StandardFileReader(),
            frontmatter_parser=StandardFrontmatterParser(),
            markdown_parser=MistuneMarkdownParser(),
            duration_parser=RegexDurationParser()
        )

    @staticmethod
    def create_file_reader():  # pragma: no cover
        """Create standard file reader"""
        return StandardFileReader()

    @staticmethod
    def create_frontmatter_parser():  # pragma: no cover
        """Create standard frontmatter parser"""
        return StandardFrontmatterParser()

    @staticmethod
    def create_markdown_parser():  # pragma: no cover
        """Create mistune markdown parser"""
        return MistuneMarkdownParser()

    @staticmethod
    def create_duration_parser():  # pragma: no cover
        """Create regex duration parser"""
        return RegexDurationParser()

    @staticmethod
    def create_operating_hours_parser():  # pragma: no cover
        """Create regex operating hours parser"""
        return RegexOperatingHoursParser()

    @staticmethod
    def create_worlds_largest_loader() -> WorldsLargestLoader:  # pragma: no cover
        """Create World's Largest attractions loader with real dependencies"""
        return WorldsLargestLoader(
            file_reader=StandardFileReader(),
            frontmatter_parser=StandardFrontmatterParser()
        )

    @staticmethod
    def create_amusement_park_loader() -> AmusementParkLoader:  # pragma: no cover
        """Create Amusement Park loader with real dependencies"""
        return AmusementParkLoader(
            file_reader=StandardFileReader(),
            frontmatter_parser=StandardFrontmatterParser()
        )

    @staticmethod
    def create_unified_loader() -> UnifiedDataLoader:  # pragma: no cover
        """Create Unified Data Loader with real dependencies"""
        return UnifiedDataLoader(
            nps_loader=DataLoaderFactory.create_nps_loader(),
            worlds_largest_loader=DataLoaderFactory.create_worlds_largest_loader(),
            park_loader=DataLoaderFactory.create_amusement_park_loader()
        )
