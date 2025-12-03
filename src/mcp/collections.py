"""Chroma collection schemas and configuration for NPS site data."""

from dataclasses import dataclass
from typing import TypedDict


# Collection name constant
NPS_SITES_COLLECTION = "nps_sites"


class NPSSiteMetadata(TypedDict, total=False):
    """
    Metadata schema for NPS site documents in Chroma.

    Required fields:
        site_name: Original site name (e.g., "Fort Scott NHS")
        site_name_normalized: Normalized form for indexing (e.g., "fort_scott_nhs")

    Optional fields:
        lat: Latitude of visitor center
        lon: Longitude of visitor center
        visited: Whether the site has been visited
        stamps_collected: Number of cancellation stamps collected
        has_user_data: Whether user-data.md exists
        file_path: Path to the main research markdown file
        content_hash: SHA256 hash for change detection
        synced_at: ISO timestamp of last sync
    """

    # Required - indexed
    site_name: str
    site_name_normalized: str

    # Optional - indexed
    visited: bool

    # Optional - not indexed
    lat: float
    lon: float
    stamps_collected: int
    has_user_data: bool
    file_path: str
    content_hash: str
    synced_at: str


@dataclass(frozen=True)
class CollectionConfig:
    """Configuration for creating the NPS sites collection."""

    name: str = NPS_SITES_COLLECTION
    description: str = "NPS site research data with geocodes and visit tracking"

    # HNSW index parameters for better search performance
    # See: https://docs.trychroma.com/guides#changing-the-distance-function
    hnsw_space: str = "cosine"  # distance metric
    hnsw_construction_ef: int = 100  # higher = better recall, slower indexing
    hnsw_search_ef: int = 100  # higher = better recall, slower search
    hnsw_m: int = 16  # connections per node

    @property
    def metadata(self) -> dict:
        """Return collection metadata for creation."""
        return {
            "description": self.description,
            "hnsw:space": self.hnsw_space,
            "hnsw:construction_ef": self.hnsw_construction_ef,
            "hnsw:search_ef": self.hnsw_search_ef,
            "hnsw:M": self.hnsw_m,
        }


# Default collection configuration
DEFAULT_CONFIG = CollectionConfig()


# Query helpers for common filtered searches
class QueryFilters:
    """Pre-built metadata filters for common queries."""

    @staticmethod
    def unvisited() -> dict:
        """Filter for sites not yet visited."""
        return {"visited": {"$eq": False}}

    @staticmethod
    def visited() -> dict:
        """Filter for sites already visited."""
        return {"visited": {"$eq": True}}

    @staticmethod
    def by_normalized_name(normalized_name: str) -> dict:
        """Filter by normalized site name (without nps_ prefix)."""
        return {"site_name_normalized": {"$eq": normalized_name}}

    @staticmethod
    def has_coordinates() -> dict:
        """Filter for sites with geocoded coordinates."""
        return {"$and": [{"lat": {"$ne": None}}, {"lon": {"$ne": None}}]}
