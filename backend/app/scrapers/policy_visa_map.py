"""Map USCIS Policy Manual volume/part from URL to visa_type for retrieval filtering."""
import re
from typing import Optional

# (volume, part_letter) -> primary visa_type tag
VOLUME_PART_VISA: dict[tuple[int, str], str] = {
    (2, "h"): "h1b",       # Specialty Occupation Workers (H-1B, E-3)
    (2, "f"): "l1",        # Intracompany Transferees (L-1)
    (2, "g"): "o1",        # Extraordinary ability (O-1)
    (4, "a"): "asylum",
    (4, "b"): "asylum",
    (4, "c"): "asylum",
    (4, "d"): "asylum",
    (4, "e"): "asylum",
    (4, "f"): "asylum",
    (6, "a"): "green_card",
    (6, "b"): "green_card",
    # Vol 6 Part D = Surviving Relatives (INA 204(l)) — not EB-1
    # Vol 6 Part E = Employment-Based Immigration (all EB prefs) — not EB-2
    (6, "f"): "l1",
    (6, "g"): "o1",
    (6, "h"): "f1",
    (7, "a"): "green_card",
    (7, "b"): "green_card",
    (10, "a"): "h4_ead",
    (10, "b"): "h4_ead",
    (12, "a"): "f1",
    (12, "b"): "f1",
    (12, "d"): "f1",
}

CHAPTER_URL_PATTERN = re.compile(
    r"/policy-manual/volume-(\d+)-part-([a-z])-chapter-(\d+)",
    re.IGNORECASE,
)


def parse_policy_url(url: str) -> Optional[dict]:
    """Extract volume, part, chapter from a policy manual chapter URL."""
    m = CHAPTER_URL_PATTERN.search(url.lower())
    if not m:
        return None
    return {
        "volume": int(m.group(1)),
        "part": m.group(2),
        "chapter": int(m.group(3)),
    }


def visa_type_from_policy_url(url: str) -> Optional[str]:
    """Infer visa_type tag from policy manual URL structure."""
    parsed = parse_policy_url(url)
    if not parsed:
        return None
    return VOLUME_PART_VISA.get((parsed["volume"], parsed["part"]))


def metadata_from_policy_url(url: str, title: str = "") -> dict:
    """Build scrape metadata headers for ingestion pipeline."""
    parsed = parse_policy_url(url)
    meta: dict = {"source_url": url}
    if parsed:
        meta["policy_volume"] = str(parsed["volume"])
        meta["policy_part"] = parsed["part"]
        meta["policy_chapter"] = str(parsed["chapter"])
        visa = visa_type_from_policy_url(url)
        if visa:
            meta["visa_type"] = visa
    if title:
        meta["policy_title"] = title[:200]
    return meta
