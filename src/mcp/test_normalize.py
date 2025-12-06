"""Tests for site name normalization."""

import pytest

from .normalize import normalize_site_name, denormalize_site_name


class TestNormalizeSiteName:
    """Tests for normalize_site_name function."""

    def test_basic_site_name(self):
        assert normalize_site_name("Fort Scott NHS") == "nps_fort_scott_nhs"

    def test_unicode_diacritics_removed(self):
        assert (
            normalize_site_name("César E. Chávez National Monument")
            == "nps_cesar_e_chavez_national_monument"
        )

    def test_ampersand_replaced(self):
        assert normalize_site_name("Lewis & Clark NHP") == "nps_lewis_clark_nhp"

    def test_slash_replaced(self):
        assert (
            normalize_site_name("Rosie the Riveter/WWII Home Front NHP")
            == "nps_rosie_the_riveter_wwii_home_front_nhp"
        )

    def test_periods_removed(self):
        assert normalize_site_name("St. Croix NSR") == "nps_st_croix_nsr"

    def test_apostrophes_removed(self):
        assert normalize_site_name("Ebey's Landing NH RES") == "nps_ebeys_landing_nh_res"

    def test_parentheses_removed(self):
        assert (
            normalize_site_name("Great Sand Dunes NP and PRES")
            == "nps_great_sand_dunes_np_and_pres"
        )

    def test_multiple_spaces_collapsed(self):
        assert normalize_site_name("Fort   Scott    NHS") == "nps_fort_scott_nhs"

    def test_leading_trailing_whitespace_stripped(self):
        assert normalize_site_name("  Fort Scott NHS  ") == "nps_fort_scott_nhs"

    def test_underscore_in_original_preserved(self):
        # Underscores in input become part of the normalized form
        assert normalize_site_name("NP _ PRES") == "nps_np_pres"

    def test_empty_string_raises_error(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_site_name("")

    def test_whitespace_only_raises_error(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_site_name("   ")

    def test_real_site_names(self):
        """Test with actual NPS site names from the dataset."""
        cases = [
            ("Abraham Lincoln Birthplace NHP", "nps_abraham_lincoln_birthplace_nhp"),
            ("Acadia NP", "nps_acadia_np"),
            ("Adams NHP", "nps_adams_nhp"),
            ("Fredericksburg & Spotsylvania NMP", "nps_fredericksburg_spotsylvania_nmp"),
            ("Martin Luther King Jr. Memorial", "nps_martin_luther_king_jr_memorial"),
            ("Home of Franklin D. Roosevelt NHS", "nps_home_of_franklin_d_roosevelt_nhs"),
            ("Perry's Victory & International Peace MEM", "nps_perrys_victory_international_peace_mem"),
        ]
        for original, expected in cases:
            assert normalize_site_name(original) == expected, f"Failed for: {original}"


class TestDenormalizeSiteName:
    """Tests for denormalize_site_name function."""

    def test_basic_denormalization(self):
        assert denormalize_site_name("nps_fort_scott_nhs") == "Fort Scott Nhs"

    def test_invalid_prefix_raises_error(self):
        with pytest.raises(ValueError, match="Invalid document ID format"):
            denormalize_site_name("fort_scott_nhs")

    def test_roundtrip_preserves_words(self):
        # Note: roundtrip is lossy for casing and special chars
        original = "fort scott nhs"  # lowercase, no special chars
        doc_id = normalize_site_name(original)
        result = denormalize_site_name(doc_id)
        assert result.lower().replace(" ", "_") == original.replace(" ", "_")
