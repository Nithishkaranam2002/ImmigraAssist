"""
Extended fallback USCIS Policy Manual chapter URLs.

Used when dynamic TOC discovery fails. Includes volumes/parts missing from the
original 68-URL list — notably Volume 2 Part H (H-1B), Volumes 4, 5, 11.
"""

def _chapters(volume: int, part: str, count: int) -> list[str]:
    base = f"https://www.uscis.gov/policy-manual/volume-{volume}-part-{part}-chapter-"
    return [f"{base}{i}" for i in range(1, count + 1)]


# Volume 2 — Nonimmigrants (H-1B is Part H)
VOLUME_2_EXTRA = (
    _chapters(2, "c", 3)
    + _chapters(2, "d", 4)
    + _chapters(2, "e", 3)
    + _chapters(2, "g", 4)
    + _chapters(2, "h", 12)   # H-1B / E-3 — critical for cap/lottery/eligibility
    + _chapters(2, "i", 3)
    + _chapters(2, "j", 2)
    + _chapters(2, "k", 2)
    + _chapters(2, "l", 2)
    + _chapters(2, "m", 2)
)

# Volume 4 — Refugees and Asylees
VOLUME_4 = (
    _chapters(4, "a", 4)
    + _chapters(4, "b", 6)
    + _chapters(4, "c", 3)
    + _chapters(4, "d", 3)
    + _chapters(4, "e", 2)
    + _chapters(4, "f", 5)
    + _chapters(4, "g", 3)
    + _chapters(4, "h", 2)
    + _chapters(4, "i", 2)
    + _chapters(4, "j", 2)
    + _chapters(4, "k", 2)
    + _chapters(4, "l", 2)
    + _chapters(4, "m", 2)
)

# Volume 5 — Adoptions
VOLUME_5 = (
    _chapters(5, "a", 3)
    + _chapters(5, "b", 4)
    + _chapters(5, "c", 3)
    + _chapters(5, "d", 2)
    + _chapters(5, "e", 2)
    + _chapters(5, "f", 2)
    + _chapters(5, "g", 2)
    + _chapters(5, "h", 2)
)

# Volume 6 — additional immigrant parts
VOLUME_6_EXTRA = (
    _chapters(6, "a", 4)
    + _chapters(6, "c", 3)
    + _chapters(6, "h", 4)
)

# Volume 11 — Fraud and National Security
VOLUME_11 = (
    _chapters(11, "a", 3)
    + _chapters(11, "b", 3)
    + _chapters(11, "c", 3)
    + _chapters(11, "d", 2)
    + _chapters(11, "e", 2)
    + _chapters(11, "f", 2)
    + _chapters(11, "g", 2)
    + _chapters(11, "h", 2)
)

# Volume 3 — additional humanitarian parts
VOLUME_3_EXTRA = (
    _chapters(3, "a", 3)
    + _chapters(3, "d", 3)
    + _chapters(3, "e", 2)
    + _chapters(3, "f", 2)
)

EXTENDED_CHAPTER_URLS: list[str] = sorted(
    set(VOLUME_2_EXTRA + VOLUME_4 + VOLUME_5 + VOLUME_6_EXTRA + VOLUME_11 + VOLUME_3_EXTRA)
)

# Target for completeness tracking (~original 68 + extended manifest)
POLICY_CHAPTER_TARGET = 200
