"""USCIS Policy Manual URL helpers and fallback chapter registry."""
import re

POLICY_BASE = "https://www.uscis.gov/policy-manual"

# Realistic target for a fully indexed policy manual (discovery + fallback)
POLICY_CHAPTER_TARGET = 120

POLICY_INDEX_URLS = [
    f"{POLICY_BASE}",
    f"{POLICY_BASE}/table-of-contents",
]

VOLUME_INDEX_URLS = [f"{POLICY_BASE}/volume-{n}" for n in range(1, 13)]

CHAPTER_URL_RE = re.compile(
    r"https?://www\.uscis\.gov/policy-manual/volume-\d+-part-[a-z]+-chapter-\d+",
    re.IGNORECASE,
)
PART_URL_RE = re.compile(
    r"https?://www\.uscis\.gov/policy-manual/volume-\d+-part-[a-z]+$",
    re.IGNORECASE,
)


def parse_policy_url(url: str) -> dict[str, str]:
    """Extract Vol/Part/Chapter labels from a policy manual chapter URL."""
    match = re.search(
        r"volume-(\d+)-part-([a-z]+)-chapter-(\d+)",
        url,
        re.IGNORECASE,
    )
    if not match:
        return {}
    vol, part, chapter = match.groups()
    return {
        "volume": f"Vol {vol}",
        "part": f"Part {part.upper()}",
        "chapter": f"Ch {chapter}",
        "section": f"USCIS Policy Manual Vol {vol} Part {part.upper()} Ch {chapter}",
    }


def is_chapter_url(url: str) -> bool:
    return bool(CHAPTER_URL_RE.match(url.split("#")[0].split("?")[0]))


def is_part_url(url: str) -> bool:
    return bool(PART_URL_RE.match(url.split("#")[0].split("?")[0]))


def normalize_policy_url(url: str) -> str:
    return url.split("#")[0].split("?")[0].rstrip("/")


# Core fallback chapters (employment + common topics)
DIRECT_CHAPTER_URLS: list[str] = [
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-1-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-1-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-2-part-f-chapter-5",
    "https://www.uscis.gov/policy-manual/volume-3-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-3-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-3-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-3-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-3-part-c-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-3-part-c-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-4-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-4-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-4-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-4-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-4-part-c-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-4-part-d-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-4-part-e-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-5-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-5-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-6-part-b-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-6-part-d-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-d-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-d-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-6-part-e-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-e-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-6-part-f-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-6-part-g-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-6-part-g-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-6-part-g-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-7-part-a-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-7-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-7-part-c-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-7-part-c-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-8-part-g-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-9-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-9-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-9-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-9-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-10-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-10-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-10-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-10-part-c-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-11-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-11-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-11-part-c-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-12-part-a-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-12-part-a-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-3",
    "https://www.uscis.gov/policy-manual/volume-12-part-b-chapter-4",
    "https://www.uscis.gov/policy-manual/volume-12-part-d-chapter-1",
    "https://www.uscis.gov/policy-manual/volume-12-part-d-chapter-2",
    "https://www.uscis.gov/policy-manual/volume-12-part-d-chapter-3",
]

DISCOVERY_SEED_URLS = list(
    dict.fromkeys(POLICY_INDEX_URLS + VOLUME_INDEX_URLS + DIRECT_CHAPTER_URLS)
)

LINK_EXTRACT_JS = """() => {
    const urls = [];
    for (const a of document.querySelectorAll('a[href]')) {
        const href = a.href.split('#')[0].split('?')[0].replace(/\\/$/, '');
        if (href.includes('/policy-manual/volume-')) urls.push(href);
    }
    return [...new Set(urls)];
}"""
