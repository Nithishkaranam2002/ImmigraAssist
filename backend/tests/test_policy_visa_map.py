"""Regression tests: Volume 6 D/E must not poison EB-1 / EB-2 retrieval."""
from app.scrapers.policy_visa_map import metadata_from_policy_url, visa_type_from_policy_url


def test_volume_6_part_d_surviving_relatives_is_not_tagged_eb1():
    """Vol 6 Part D is Surviving Relatives, not EB-1 extraordinary ability."""
    url = "https://www.uscis.gov/policy-manual/volume-6-part-d-chapter-1"
    assert visa_type_from_policy_url(url) is None
    assert "visa_type" not in metadata_from_policy_url(url)


def test_volume_6_part_e_employment_based_is_not_tagged_eb2():
    """Vol 6 Part E covers all employment-based prefs, not EB-2 alone."""
    url = "https://www.uscis.gov/policy-manual/volume-6-part-e-chapter-1"
    assert visa_type_from_policy_url(url) is None
    assert "visa_type" not in metadata_from_policy_url(url)


def test_volume_6_part_d_and_e_chapters_stay_unmapped():
    for part, chapter in (("d", 1), ("d", 2), ("d", 3), ("e", 1), ("e", 2)):
        url = (
            f"https://www.uscis.gov/policy-manual/"
            f"volume-6-part-{part}-chapter-{chapter}"
        )
        assert visa_type_from_policy_url(url) is None
