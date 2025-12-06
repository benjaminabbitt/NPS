"""
Sync NPS site data from filesystem to Chroma vector database.

Scans 2-Enhanced Data/NPS/ directories and syncs to the unified nps_sites collection.
Uses content hashing for change detection and maintains a sync manifest.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
import yaml

from .collections import NPS_SITES_COLLECTION, NPSSiteMetadata, DEFAULT_CONFIG
from .normalize import normalize_site_name


def get_chroma_data_dir(workspace_path: Path | None = None) -> Path:
    """
    Read Chroma data directory from .mcp.json config.

    Args:
        workspace_path: Path to workspace root (defaults to current working directory)

    Returns:
        Path to Chroma data directory
    """
    if workspace_path is None:
        workspace_path = Path.cwd()

    mcp_config_path = workspace_path / ".mcp.json"

    if not mcp_config_path.exists():
        # Default fallback
        return workspace_path / "chroma.db"

    with open(mcp_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Extract data-dir from chroma server args
    chroma_config = config.get("mcpServers", {}).get("chroma", {})
    args = chroma_config.get("args", [])

    # Find --data-dir argument
    for i, arg in enumerate(args):
        if arg == "--data-dir" and i + 1 < len(args):
            data_dir = args[i + 1]
            # Handle relative paths
            if not Path(data_dir).is_absolute():
                return workspace_path / data_dir
            return Path(data_dir)

    # Default fallback
    return workspace_path / "chroma.db"


def get_chroma_client(workspace_path: Path | None = None) -> chromadb.ClientAPI:
    """
    Get a Chroma client connected to the MCP-configured database.

    Args:
        workspace_path: Path to workspace root

    Returns:
        Chroma PersistentClient
    """
    data_dir = get_chroma_data_dir(workspace_path)
    return chromadb.PersistentClient(path=str(data_dir))


@dataclass
class SiteData:
    """Parsed data from an NPS site directory."""

    site_name: str
    doc_id: str
    content: str
    content_hash: str
    file_path: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    visited: bool = False
    stamps_collected: int = 0
    has_user_data: bool = False

    def to_metadata(self) -> NPSSiteMetadata:
        """Convert to Chroma metadata dict."""
        # Extract normalized name without prefix
        normalized = self.doc_id[4:] if self.doc_id.startswith("nps_") else self.doc_id

        metadata: NPSSiteMetadata = {
            "site_name": self.site_name,
            "site_name_normalized": normalized,
            "visited": self.visited,
            "has_user_data": self.has_user_data,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "synced_at": datetime.now().isoformat(),
        }

        if self.lat is not None:
            metadata["lat"] = self.lat
        if self.lon is not None:
            metadata["lon"] = self.lon
        if self.stamps_collected > 0:
            metadata["stamps_collected"] = self.stamps_collected

        return metadata


@dataclass
class SyncManifest:
    """Tracks sync state for change detection."""

    sites: dict[str, dict] = field(default_factory=dict)
    last_sync: Optional[str] = None

    @classmethod
    def load(cls, path: Path) -> "SyncManifest":
        """Load manifest from file."""
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            sites=data.get("sites", {}),
            last_sync=data.get("last_sync"),
        )

    def save(self, path: Path) -> None:
        """Save manifest to file."""
        self.last_sync = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"sites": self.sites, "last_sync": self.last_sync},
                f,
                indent=2,
            )

    def needs_sync(self, doc_id: str, content_hash: str) -> bool:
        """Check if a site needs to be synced based on content hash."""
        if doc_id not in self.sites:
            return True
        return self.sites[doc_id].get("content_hash") != content_hash

    def mark_synced(self, doc_id: str, content_hash: str) -> None:
        """Mark a site as synced."""
        self.sites[doc_id] = {
            "content_hash": content_hash,
            "synced_at": datetime.now().isoformat(),
        }


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for change detection."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def parse_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """
    Extract YAML frontmatter from markdown content.

    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return {}, content

    frontmatter_str = content[3 : end_match.start() + 3]
    remaining_content = content[end_match.end() + 3 :]

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        return {}, content

    return frontmatter, remaining_content


def parse_user_data(user_data_path: Path) -> tuple[bool, int]:
    """
    Parse user-data.md to extract visited status and stamps collected.

    Returns:
        Tuple of (visited, stamps_collected)
    """
    if not user_data_path.exists():
        return False, 0

    content = user_data_path.read_text(encoding="utf-8")

    # Check for visited checkbox: "- [x] Visited" or "- [X] Visited"
    visited = bool(re.search(r"- \[[xX]\] Visited", content))

    # Count checked stamp checkboxes in Cancellation Stamps section
    stamps_section = re.search(
        r"## Cancellation Stamps\s*\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    stamps_collected = 0
    if stamps_section:
        stamps_collected = len(re.findall(r"- \[[xX]\]", stamps_section.group(1)))

    return visited, stamps_collected


def scan_site_directory(site_dir: Path) -> Optional[SiteData]:
    """
    Scan a single NPS site directory and extract all data.

    Args:
        site_dir: Path to site directory (e.g., "2-Enhanced Data/NPS/Fort Scott NHS/")

    Returns:
        SiteData if valid site found, None otherwise
    """
    site_name = site_dir.name

    # Find the main report file
    main_report = None

    # Try exact match first
    exact_match = site_dir / f"{site_name}.md"
    if exact_match.exists():
        main_report = exact_match
    else:
        # Look for any .md file that's not user-data.md
        for md_file in site_dir.glob("*.md"):
            if md_file.name != "user-data.md":
                main_report = md_file
                break

    if not main_report or not main_report.exists():
        return None

    # Read main report
    content = main_report.read_text(encoding="utf-8")
    if not content.strip():
        return None

    # Parse frontmatter for geocode
    frontmatter, _ = parse_yaml_frontmatter(content)
    lat, lon = None, None
    if "geocode" in frontmatter:
        geocode = frontmatter["geocode"]
        if isinstance(geocode, dict) and "visitor_center" in geocode:
            coords = geocode["visitor_center"]
            if isinstance(coords, list) and len(coords) >= 2:
                lat, lon = coords[0], coords[1]

    # Parse user data
    user_data_path = site_dir / "user-data.md"
    visited, stamps_collected = parse_user_data(user_data_path)

    # Generate doc ID and hash
    doc_id = normalize_site_name(site_name)
    content_hash = compute_content_hash(content)

    return SiteData(
        site_name=site_name,
        doc_id=doc_id,
        content=content,
        content_hash=content_hash,
        file_path=str(main_report.relative_to(main_report.parents[2])),
        lat=lat,
        lon=lon,
        visited=visited,
        stamps_collected=stamps_collected,
        has_user_data=user_data_path.exists(),
    )


def scan_all_sites(base_path: Path) -> list[SiteData]:
    """
    Scan all NPS site directories.

    Args:
        base_path: Path to "2-Enhanced Data/NPS/" directory

    Returns:
        List of SiteData for all valid sites
    """
    sites = []
    for site_dir in sorted(base_path.iterdir()):
        if not site_dir.is_dir():
            continue
        site_data = scan_site_directory(site_dir)
        if site_data:
            sites.append(site_data)
    return sites


@dataclass
class SyncResult:
    """Results from a sync operation."""

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total_synced(self) -> int:
        return len(self.added) + len(self.updated)

    def summary(self) -> str:
        lines = [
            f"Sync complete:",
            f"  Added: {len(self.added)}",
            f"  Updated: {len(self.updated)}",
            f"  Skipped (unchanged): {len(self.skipped)}",
        ]
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for site, error in self.errors[:5]:
                lines.append(f"    - {site}: {error}")
        return "\n".join(lines)


def prepare_sync_batches(
    sites: list[SiteData],
    manifest: SyncManifest,
    batch_size: int = 50,
) -> tuple[list[list[SiteData]], list[str]]:
    """
    Prepare batches of sites that need syncing.

    Returns:
        Tuple of (batches_to_sync, skipped_doc_ids)
    """
    to_sync = []
    skipped = []

    for site in sites:
        if manifest.needs_sync(site.doc_id, site.content_hash):
            to_sync.append(site)
        else:
            skipped.append(site.doc_id)

    # Split into batches
    batches = []
    for i in range(0, len(to_sync), batch_size):
        batches.append(to_sync[i : i + batch_size])

    return batches, skipped


def sync_to_chroma(
    workspace_path: Path | None = None,
    nps_data_path: Path | None = None,
    manifest_path: Path | None = None,
    batch_size: int = 50,
    force: bool = False,
) -> SyncResult:
    """
    Sync all NPS site data to Chroma.

    Args:
        workspace_path: Path to workspace root (for .mcp.json)
        nps_data_path: Path to NPS data directory (defaults to 2-Enhanced Data/NPS/)
        manifest_path: Path to sync manifest (defaults to .chroma_sync_manifest.json)
        batch_size: Number of documents per batch
        force: If True, sync all sites regardless of content hash

    Returns:
        SyncResult with counts of added, updated, skipped, and errors
    """
    if workspace_path is None:
        workspace_path = Path.cwd()

    if nps_data_path is None:
        nps_data_path = workspace_path / "2-Enhanced Data" / "NPS"

    if manifest_path is None:
        manifest_path = workspace_path / ".chroma_sync_manifest.json"

    # Load manifest (or create empty if forcing)
    manifest = SyncManifest() if force else SyncManifest.load(manifest_path)

    # Scan all sites
    print(f"Scanning {nps_data_path}...")
    sites = scan_all_sites(nps_data_path)
    print(f"Found {len(sites)} sites")

    # Prepare batches
    batches, skipped = prepare_sync_batches(sites, manifest, batch_size)
    print(f"Sites to sync: {sum(len(b) for b in batches)}")
    print(f"Sites unchanged: {len(skipped)}")

    if not batches:
        return SyncResult(skipped=skipped)

    # Connect to Chroma
    client = get_chroma_client(workspace_path)

    # Get or create collection
    try:
        collection = client.get_collection(name=NPS_SITES_COLLECTION)
        print(f"Using existing collection: {NPS_SITES_COLLECTION}")
    except Exception:
        collection = client.create_collection(
            name=NPS_SITES_COLLECTION,
            metadata=DEFAULT_CONFIG.metadata,
        )
        print(f"Created collection: {NPS_SITES_COLLECTION}")

    # Get existing IDs to determine add vs update
    existing_ids = set()
    try:
        existing = collection.get(include=[])
        existing_ids = set(existing["ids"])
    except Exception:
        pass

    result = SyncResult(skipped=skipped)

    # Process batches
    for batch_num, batch in enumerate(batches):
        print(f"Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} sites)...")

        # Separate into add and update
        to_add = [s for s in batch if s.doc_id not in existing_ids]
        to_update = [s for s in batch if s.doc_id in existing_ids]

        # Add new documents
        if to_add:
            try:
                collection.add(
                    documents=[s.content for s in to_add],
                    ids=[s.doc_id for s in to_add],
                    metadatas=[s.to_metadata() for s in to_add],
                )
                for s in to_add:
                    result.added.append(s.doc_id)
                    manifest.mark_synced(s.doc_id, s.content_hash)
            except Exception as e:
                for s in to_add:
                    result.errors.append((s.doc_id, str(e)))

        # Update existing documents
        if to_update:
            try:
                collection.update(
                    documents=[s.content for s in to_update],
                    ids=[s.doc_id for s in to_update],
                    metadatas=[s.to_metadata() for s in to_update],
                )
                for s in to_update:
                    result.updated.append(s.doc_id)
                    manifest.mark_synced(s.doc_id, s.content_hash)
            except Exception as e:
                for s in to_update:
                    result.errors.append((s.doc_id, str(e)))

    # Save manifest
    manifest.save(manifest_path)
    print(f"Manifest saved to {manifest_path}")

    return result


def main():
    """CLI entry point for sync."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync NPS data to Chroma")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync all sites regardless of content hash",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of documents per batch (default: 50)",
    )
    args = parser.parse_args()

    result = sync_to_chroma(force=args.force, batch_size=args.batch_size)
    print()
    print(result.summary())


if __name__ == "__main__":
    main()
