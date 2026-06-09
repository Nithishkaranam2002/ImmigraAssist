from dataclasses import dataclass
from enum import Enum
import re
from app.utils.logger import logger
from typing import Optional


class ModerationStatus(str, Enum):
    SAFE = "safe"
    BLOCKED = "blocked"
    WARNING = "warning"


@dataclass
class ModerationResult:
    status: ModerationStatus
    reason: Optional[str]
    original_query: str
    is_safe: bool


# immigration law keywords — query must be somewhat related to these
IMMIGRATION_KEYWORDS = [
    "visa", "immigration", "uscis", "petition", "asylum", "green card",
    "work permit", "ead", "i-140", "i-485", "i-765", "i-131", "i-20", "i-94",
    "h1b", "h4", "l1", "o1", "eb1", "eb2", "f1", "b1", "b2", "j1", "tn",
    "naturalization", "citizenship", "deportation", "removal",
    "appeal", "denial", "approval", "case", "filing", "form",
    "policy", "regulation", "section", "clause", "law", "rule",
    "attorney", "lawyer", "client", "firm", "hearing", "court",
    "dependent", "spouse", "employer", "employee", "petition",
    "priority date", "labor certification", "perm", "ac21",
    "portability", "extension", "renewal", "status", "overstay",
    "cap", "lottery", "quota", "nonimmigrant", "beneficiary",
    # F-1 / student pathways
    "opt", "stem opt", "cpt", "sevis", "dso", "practical training",
    "curricular practical", "optional practical", "student visa",
    "stem degree", "grace period",
]

# Topic patterns that are clearly immigration even without keyword hits
IMMIGRATION_TOPIC_PATTERNS = [
    re.compile(r"\b(opt\b|stem\s+opt|cpt\b|curricular\s+practical)", re.I),
    re.compile(r"\b(cap|lottery|lca\b|premium\s+processing)", re.I),
    re.compile(r"\b(ead|work\s+auth|employment\s+authorization)", re.I),
    re.compile(r"\b(adjustment\s+of\s+status|consular\s+processing)", re.I),
    re.compile(r"\b(i-140|i-485|i-765|i-129|i-539|i-20|i-94)\b", re.I),
    re.compile(r"\b(h[-\s]?1b|h[-\s]?4|l[-\s]?1|o[-\s]?1|eb[-\s]?[12]|f[-\s]?1)\b", re.I),
]

# normalize hyphenated visa codes so "H-1B" matches keyword "h1b"
VISA_NORMALIZATIONS = [
    (re.compile(r"\bh[-\s]?1b\b", re.IGNORECASE), "h1b"),
    (re.compile(r"\bh[-\s]?4\b", re.IGNORECASE), "h4"),
    (re.compile(r"\bl[-\s]?1[ab]?\b", re.IGNORECASE), "l1"),
    (re.compile(r"\bo[-\s]?1\b", re.IGNORECASE), "o1"),
    (re.compile(r"\beb[-\s]?1\b", re.IGNORECASE), "eb1"),
    (re.compile(r"\beb[-\s]?2\b", re.IGNORECASE), "eb2"),
    (re.compile(r"\bf[-\s]?1\b", re.IGNORECASE), "f1"),
    (re.compile(r"\bb[-\s]?1\b", re.IGNORECASE), "b1"),
    (re.compile(r"\bb[-\s]?2\b", re.IGNORECASE), "b2"),
]

# blocked patterns — queries that should never be processed
BLOCKED_PATTERNS = [
    re.compile(r"\b(ignore|forget|override)\s+(your\s+)?(instructions|rules|guidelines|system\s+prompt)\b", re.IGNORECASE),
    re.compile(r"\b(jailbreak|bypass|hack|exploit)\b", re.IGNORECASE),
    re.compile(r"\b(pretend|act as|you are now|roleplay as)\b", re.IGNORECASE),
    re.compile(r"\b(bomb|weapon|kill|murder|terrorist)\b", re.IGNORECASE),
    re.compile(r"(```|<script|<\/script|SELECT\s+\*\s+FROM)", re.IGNORECASE),  # injection attempts
]

# warning patterns — allow but log
WARNING_PATTERNS = [
    re.compile(r"\b(ssn|social security|passport number|alien number)\b", re.IGNORECASE),
    re.compile(r"\b(confidential|private|secret)\b", re.IGNORECASE),
]


class ContentModerator:
    """
    Moderates incoming queries before processing.

    Two layers:
    1. Hard block — injection attempts, jailbreaks, clearly harmful content
    2. Scope check — query should be immigration-law related
    3. Warning — sensitive terms flagged but allowed through

    LlamaGuard integration is included as an optional upgrade.
    The rule-based layer runs first (fast, no model needed).
    LlamaGuard runs on edge cases the rules don't clearly handle.
    """

    def __init__(self):
        self.llamaguard_available = False
        # LlamaGuard can be plugged in here when GPU is available
        # self.llamaguard = LlamaGuardClient(settings.LLAMAGUARD_MODEL)
        logger.info("Content moderator initialized (rule-based mode)")

    def _normalize_for_scope(self, query: str) -> str:
        """Collapse H-1B-style spellings so scope keywords match."""
        normalized = query.lower()
        for pattern, replacement in VISA_NORMALIZATIONS:
            normalized = pattern.sub(replacement, normalized)
        return normalized

    def _immigration_score(self, query: str) -> int:
        normalized = self._normalize_for_scope(query)
        score = 0
        for kw in IMMIGRATION_KEYWORDS:
            if len(kw) <= 4:
                if re.search(rf"\b{re.escape(kw)}\b", normalized):
                    score += 1
            elif kw in normalized:
                score += 1
        return score

    def _is_immigration_topic(self, query: str) -> bool:
        return any(p.search(query) for p in IMMIGRATION_TOPIC_PATTERNS)

    def moderate(self, query: str) -> ModerationResult:
        """
        Main entry point.
        Returns ModerationResult with safe/blocked/warning status.
        """
        if not query or not query.strip():
            return ModerationResult(
                status=ModerationStatus.BLOCKED,
                reason="Empty query",
                original_query=query,
                is_safe=False,
            )

        # ── Layer 1: Hard block patterns ───────────────────────────────
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(query):
                logger.warning(f"Query blocked by hard pattern: '{query[:80]}'")
                return ModerationResult(
                    status=ModerationStatus.BLOCKED,
                    reason="Query contains prohibited content",
                    original_query=query,
                    is_safe=False,
                )

        # ── Layer 2: Scope check ───────────────────────────────────────
        immigration_score = self._immigration_score(query)

        # short queries get a pass — could be a follow-up ("what about that?")
        if (
            len(query.split()) > 6
            and immigration_score == 0
            and not self._is_immigration_topic(query)
        ):
            logger.warning(f"Query out of scope: '{query[:80]}'")
            return ModerationResult(
                status=ModerationStatus.BLOCKED,
                reason=(
                    "This tool is specialized for US immigration law. "
                    "Please ask questions related to visas, USCIS policies, "
                    "or immigration cases."
                ),
                original_query=query,
                is_safe=False,
            )

        # ── Layer 3: Warning check ─────────────────────────────────────
        for pattern in WARNING_PATTERNS:
            if pattern.search(query):
                logger.info(f"Query flagged with warning: '{query[:80]}'")
                return ModerationResult(
                    status=ModerationStatus.WARNING,
                    reason="Query contains sensitive terms — proceed with caution",
                    original_query=query,
                    is_safe=True,  # allowed through but flagged
                )

        return ModerationResult(
            status=ModerationStatus.SAFE,
            reason=None,
            original_query=query,
            is_safe=True,
        )

    def moderate_with_llamaguard(self, query: str) -> ModerationResult:
        """
        Optional upgrade — runs LlamaGuard model on the query.
        Use this when you have GPU available and want stronger moderation.

        To enable:
        1. pip install transformers accelerate
        2. Set LLAMAGUARD_MODEL in .env
        3. Replace self.moderate() calls with this method
        """
        # first run rule-based check
        rule_result = self.moderate(query)
        if not rule_result.is_safe:
            return rule_result

        # then run LlamaGuard on top
        # this is where you'd call the model
        # keeping as stub for now — plug in when GPU is ready
        logger.info("LlamaGuard check — (stub, plug in model here)")
        return rule_result