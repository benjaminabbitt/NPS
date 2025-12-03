"""Site name normalization for consistent Chroma document IDs."""

import re
import unicodedata


def normalize_site_name(name: str) -> str:
    """
    Normalize an NPS site name into a consistent Chroma document ID.

    Transformation rules:
    1. Remove apostrophes (both straight ' and curly ') - keeps word intact
    2. Unicode normalize (NFKD) and strip diacritics (é → e)
    3. Lowercase
    4. Replace special characters and whitespace with underscores
    5. Collapse multiple underscores
    6. Strip leading/trailing underscores
    7. Prefix with 'nps_'

    Examples:
        >>> normalize_site_name("Fort Scott NHS")
        'nps_fort_scott_nhs'
        >>> normalize_site_name("César E. Chávez National Monument")
        'nps_cesar_e_chavez_national_monument'
        >>> normalize_site_name("Lewis & Clark NHP")
        'nps_lewis_clark_nhp'
        >>> normalize_site_name("Rosie the Riveter/WWII Home Front NHP")
        'nps_rosie_the_riveter_wwii_home_front_nhp'
        >>> normalize_site_name("Perry's Victory")
        'nps_perrys_victory'

    Args:
        name: Original site name (e.g., "Fort Scott NHS")

    Returns:
        Normalized document ID (e.g., "nps_fort_scott_nhs")
    """
    if not name or not name.strip():
        raise ValueError("Site name cannot be empty")

    # Remove apostrophes first (keeps possessives intact like "Perry's" -> "Perrys")
    normalized = name.replace("'", "").replace("'", "").replace("'", "")

    # Unicode normalize and remove diacritics
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))

    # Lowercase
    normalized = normalized.lower()

    # Replace special chars with underscores (keep alphanumeric only)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)

    # Collapse multiple underscores
    normalized = re.sub(r"_+", "_", normalized)

    # Strip leading/trailing underscores
    normalized = normalized.strip("_")

    # Prefix with nps_
    return f"nps_{normalized}"


def denormalize_site_name(doc_id: str) -> str:
    """
    Convert a normalized document ID back to a human-readable form.

    Note: This is lossy - original casing and special characters cannot be recovered.

    Args:
        doc_id: Normalized document ID (e.g., "nps_fort_scott_nhs")

    Returns:
        Human-readable form (e.g., "Fort Scott Nhs")
    """
    if not doc_id.startswith("nps_"):
        raise ValueError(f"Invalid document ID format: {doc_id}")

    # Remove prefix
    name = doc_id[4:]

    # Replace underscores with spaces and title case
    return name.replace("_", " ").title()
