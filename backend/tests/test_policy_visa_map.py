from app.scrapers.policy_visa_map import metadata_from_policy_url, visa_type_from_policy_url
from app.scrapers.uscis_policy_scraper import ALL_FALLBACK_CHAPTER_URLS


def test_volume_2_part_f_student_chapters_are_tagged_as_f1():
    url = "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-6"

    assert visa_type_from_policy_url(url) == "f1"
    assert metadata_from_policy_url(url)["visa_type"] == "f1"


def test_volume_2_part_g_e_visa_chapters_are_not_tagged_as_o1():
    url = "https://www.uscis.gov/policy-manual/volume-2-part-g-chapter-1"

    assert visa_type_from_policy_url(url) is None
    assert "visa_type" not in metadata_from_policy_url(url)


def test_fallback_manifest_includes_all_known_student_chapters():
    for chapter in range(6, 10):
        assert (
            f"https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-{chapter}"
            in ALL_FALLBACK_CHAPTER_URLS
        )
