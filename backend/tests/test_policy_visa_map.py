"""Regression tests for policy URL → visa_type tagging."""
from app.scrapers.policy_visa_map import metadata_from_policy_url, visa_type_from_policy_url


def test_volume_12_citizenship_is_not_tagged_as_f1():
    """Vol 12 is Citizenship & Naturalization — tagging as f1 poisons student retrieval."""
    for part, chapter in (("a", 1), ("b", 2), ("d", 1)):
        url = f"https://www.uscis.gov/policy-manual/volume-12-part-{part}-chapter-{chapter}"
        assert visa_type_from_policy_url(url) is None
        assert "visa_type" not in metadata_from_policy_url(url)


def test_volume_6_employment_and_investor_parts_are_not_mis_tagged():
    """Vol 6 F/G/H were wrongly l1/o1/f1; leave unmapped rather than poison filters."""
    assert visa_type_from_policy_url(
        "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-1"
    ) is None
    assert visa_type_from_policy_url(
        "https://www.uscis.gov/policy-manual/volume-6-part-g-chapter-1"
    ) is None
    assert visa_type_from_policy_url(
        "https://www.uscis.gov/policy-manual/volume-6-part-h-chapter-1"
    ) is None


def test_volume_2_part_f_students_tagged_f1():
    url = "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-6"
    assert visa_type_from_policy_url(url) == "f1"
    assert metadata_from_policy_url(url)["visa_type"] == "f1"


def test_volume_2_part_g_e_visa_not_tagged_o1():
    url = "https://www.uscis.gov/policy-manual/volume-2-part-g-chapter-1"
    assert visa_type_from_policy_url(url) is None


def test_volume_2_part_l_intracompany_tagged_l1():
    url = "https://www.uscis.gov/policy-manual/volume-2-part-l-chapter-1"
    assert visa_type_from_policy_url(url) == "l1"


def test_volume_10_still_tagged_h4_ead():
    url = "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-1"
    assert visa_type_from_policy_url(url) == "h4_ead"
