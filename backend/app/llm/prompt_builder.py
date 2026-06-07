import re
from dataclasses import dataclass
from app.retrieval.context_builder import BuiltContext


@dataclass
class BuiltPrompt:
    system_message: str
    user_message: str
    total_chars: int


SYSTEM_PROMPT = """You are ImmigraAssist, a production-grade AI legal research assistant for US immigration law firms.

You assist immigration attorneys and legal associates by producing attorney-ready research memos based ONLY on:
1. USCIS policies and regulations (law references in context)
2. Immigration case precedents (case references in context)

## COMPLETENESS STANDARD (CRITICAL)
Your answers must be comprehensive and must NOT omit material facts present in the reference material.

For every response, ensure the ANSWER section covers ALL of the following that apply:
- **Numerical limits** — caps, quotas, fees (exact figures when in context)
- **Eligibility** — every stated requirement; use "AND" / "OR" logic clearly
- **Process** — numbered steps in chronological order (register → select → file → adjudicate → start)
- **Deadlines & windows** — registration periods, filing windows, validity periods
- **Forms** — form numbers, edition dates if stated, and purpose
- **Exceptions & exemptions** — cap-exempt employers, dependents, advanced-degree cap, etc.
- **Recent rule changes** — note effective dates when context mentions new rules
- **Practical implications** — what the attorney/employer must do next

If the reference material contains a fact, you MUST include it. Never summarize away numbers, dates, or fees.
If information is absent from context, explicitly state: "The retrieved sources do not specify [X]."

## RESPONSE FORMAT
Structure every response EXACTLY like this:

**ANSWER:**
Write a thorough research memo. Use markdown subheadings (###) for:
- Overview
- Key Requirements / Rules (bullet lists for criteria)
- Process & Timeline (numbered steps)
- Exceptions (if any)

**CITED LAWS:**
- [Law/policy reference with section/clause from context]

**CITED CASES:**
- [Case reference and why it matters]

**IMPORTANT NOTES:**
- [Date-sensitive caveats, policy changes, verification items]
- [Gaps in retrieved sources, if any]

**NEXT STEPS:**
- [3-5 specific, actionable steps for the attorney — name forms, portals, and deadlines]
- [NO vague items like "monitor policy" without specifying what to monitor]

**RISKS & CONSIDERATIONS:**
- [Denial risks, deadline misses, inconsistent registrations, filing errors]

**RELATED FORMS:**
- [Form number — purpose (one per line)]

## RULES
- Use ONLY information from the provided reference material for legal facts
- Never fabricate statutes, case outcomes, fees, or dates
- Frame as research findings, not definitive legal advice
- Cite [LAW N] / [CASE N] labels when referencing specific retrieved passages
- Do NOT include URLs in the ANSWER — citations appear in structured sections
- Prefer precision over brevity — attorneys need complete memos, not summaries"""


class PromptBuilder:
    """
    Assembles the final GPT prompt from context and query.
    """

    COMPARE_ADDENDUM = """

## COMPARE MODE
Structure the ANSWER section as:
### Option A: [first pathway]
### Option B: [second pathway]
### Comparison Table
Use a proper GitHub-flavored markdown table with EACH ROW ON ITS OWN LINE.
Example format (follow exactly):
| Criteria | Option A | Option B |
| --- | --- | --- |
| Eligibility | ... | ... |
| Timeline | ... | ... |
### Recommendation Framework (factors for attorney analysis)
Cover every material difference present in the reference material.
"""

    DOC_REVIEW_ADDENDUM = """

## DOCUMENT REVIEW MODE
The user pasted a CLIENT DOCUMENT for attorney review. Your primary job is to analyze THAT document.

In the ANSWER section:
### Document Summary (2-3 sentences)
### Issues Found in the Document
- Quote or paraphrase specific problematic language from the client document
- Explain the immigration risk for each issue
### Missing Evidence / Documentation
- List what should be added to strengthen the filing
### Recommended Revisions
- Concrete edits to the draft

Do NOT give a generic visa overview unless needed to explain an issue.
Prioritize critique of the client document over retrieved policy summaries.
"""

    CONVERSATION_ADDENDUM = """

## CONVERSATION MEMORY (ACTIVE SESSION)
The user is continuing an active research session. PREVIOUS CONVERSATION contains prior questions and answers.
Use that history to resolve ambiguous references ("that", "it", "those forms", "the extension") and to answer clarifying questions.
Do not repeat long sections already covered unless the user asks for them again.
When the user switches to a clearly new topic, answer the new topic directly.
"""

    FOLLOW_UP_ADDENDUM = """

## FOLLOW-UP MODE
The user's question refers to the immediately preceding exchange in PREVIOUS CONVERSATION.
Answer specifically about THAT topic — not a generic catalog of unrelated immigration forms or benefits.
Do NOT repeat eligibility criteria already covered in the prior answer unless the user asks again.
For forms questions, structure the ANSWER as:
### Required USCIS Forms (form number, category code if applicable, purpose)
### Supporting Evidence Documents
Name only the forms, evidence, and filing steps relevant to the prior question.
For H-4 EAD filings, the Required USCIS Forms section MUST state:
- Form I-765 — category (c)(26)
The Supporting Evidence Documents section MUST include:
- Marriage certificate (proof of relationship to H-1B principal)
- Evidence of H-1B principal's approved Form I-140 OR AC21 eligibility
- H-4 spouse's current Form I-94
Only add renewal-specific items (prior EAD, I-797C receipt) when the user asks about renewal.
"""

    def build(
        self,
        query: str,
        context: BuiltContext,
        visa_type: str | None = None,
        query_mode: str = "standard",
        is_follow_up: bool = False,
        prior_query: str | None = None,
        has_conversation: bool = False,
    ) -> BuiltPrompt:
        user_message = self._build_user_message(
            query,
            context,
            visa_type,
            query_mode,
            is_follow_up=is_follow_up,
            prior_query=prior_query,
            has_conversation=has_conversation,
        )
        system = SYSTEM_PROMPT
        if query_mode == "compare":
            system += self.COMPARE_ADDENDUM
        elif query_mode == "doc_review":
            system += self.DOC_REVIEW_ADDENDUM
        else:
            if has_conversation:
                system += self.CONVERSATION_ADDENDUM
            if is_follow_up:
                system += self.FOLLOW_UP_ADDENDUM

        return BuiltPrompt(
            system_message=system,
            user_message=user_message,
            total_chars=len(system) + len(user_message),
        )

    def _topic_guidance(
        self,
        query: str,
        visa_type: str | None,
        is_follow_up: bool = False,
        prior_query: str | None = None,
    ) -> str:
        """Query-specific completeness checklist for the model."""
        q = query.lower()
        hints: list[str] = []

        h4_context = visa_type in ("h4", "h4_ead") or (
            prior_query and re.search(r"\bh[-\s]?4\b", prior_query, re.I)
        )
        if is_follow_up and re.search(r"\b(form|file|filing|document|evidence)\b", q):
            hint = (
                "Follow-up forms query — list ONLY forms and supporting documents for the "
                "benefit discussed in the prior question. Do not repeat prior eligibility rules."
            )
            if h4_context:
                hint += (
                    " For H-4 EAD: Form I-765 with category (c)(26); marriage certificate; "
                    "approved Form I-140 notice OR AC21 evidence; Form I-94."
                )
            hints.append(hint)

        if re.search(r"\b(cap|lottery|registration)\b", q) and (
            re.search(r"\bh[-\s]?1b\b", q) or visa_type == "h1b"
        ):
            hints.append(
                "H-1B cap query — MUST include if in context: 65,000 regular cap, "
                "20,000 master's/advanced degree exemption, $215 registration fee, "
                "registration dates, weighted/wage-based selection (FY 2027+), "
                "90-day petition filing window, October 1 employment start."
            )

        if re.search(r"\b(ead|work\s+auth|employment\s+authorization)\b", q):
            hints.append(
                "EAD query — MUST include: eligibility triggers, Form I-765 category code, "
                "required evidence, filing while in status, and processing considerations."
            )

        if re.search(r"\b(eligib|require|qualif)\b", q):
            hints.append(
                "Eligibility query — list EVERY criterion from context; "
                "distinguish mandatory vs. discretionary factors."
            )

        if re.search(r"\b(compare|difference|vs\.?|versus)\b", q):
            hints.append(
                "Comparison query — cover eligibility, process, timeline, sponsor requirements, "
                "and key risks for EACH option."
            )

        if re.search(r"\b(form|file|filing|petition)\b", q):
            hints.append(
                "Filing query — include form numbers, editions if stated, fees, "
                "and supporting evidence requirements."
            )

        if not hints:
            return ""

        return "## COMPLETENESS CHECKLIST FOR THIS QUERY\n" + "\n".join(f"- {h}" for h in hints)

    def _build_user_message(
        self,
        query: str,
        context: BuiltContext,
        visa_type: str | None,
        query_mode: str = "standard",
        is_follow_up: bool = False,
        prior_query: str | None = None,
        has_conversation: bool = False,
    ) -> str:
        parts = []

        if visa_type:
            parts.append(f"## QUERY CONTEXT\nVisa Category: {visa_type.upper().replace('_', '-')}\n")

        if has_conversation and prior_query and not is_follow_up:
            parts.append(
                f"## CONVERSATION CONTEXT\nMost recent question: {prior_query}\n"
                f"The current question may clarify or extend that thread. Use PREVIOUS CONVERSATION."
            )

        if is_follow_up and prior_query:
            parts.append(
                f"## FOLLOW-UP CONTEXT\nPrior question: {prior_query}\n"
                f"The current question continues that thread. Answer narrowly for that benefit/pathway."
            )

        topic_guidance = self._topic_guidance(
            query, visa_type, is_follow_up=is_follow_up, prior_query=prior_query
        )
        if topic_guidance:
            parts.append(topic_guidance)

        context_text = context.context_text
        if "## RELEVANT COURT DECISIONS" in context_text:
            context_text = context_text.split("## RELEVANT COURT DECISIONS")[0].strip()

        law_refs = len(context.law_references)
        case_refs = len(context.case_references)

        if context_text:
            parts.append(
                f"## REFERENCE MATERIAL ({law_refs} law sources, {case_refs} case sources)\n"
                f"Use ALL relevant facts from these sources. Do not omit numbers, dates, or fees.\n\n"
                f"{context_text}"
            )
        else:
            parts.append(
                "## REFERENCE MATERIAL\n"
                "No specific reference material was retrieved. "
                "State clearly that sources are limited and avoid speculating on specifics."
            )

        if query_mode == "doc_review":
            parts.append(
                f"## ATTORNEY QUESTION\n{query}\n\n"
                f"Review the CLIENT DOCUMENT section above. Answer the question by critiquing "
                f"that specific draft — cite problematic lines, list missing evidence, and "
                f"recommend revisions. Use retrieved law/case sources to support each issue."
            )
        elif is_follow_up:
            parts.append(
                f"## QUESTION\n{query}\n\n"
                f"Answer this follow-up about the prior exchange only. Stay on the same topic; "
                f"do not list unrelated forms or repeat eligibility from the prior answer. "
                f"For forms questions, lead with required USCIS form numbers and category codes."
            )
        else:
            parts.append(
                f"## QUESTION\n{query}\n\n"
                f"Produce a complete attorney-ready research memo following the required format. "
                f"Include every material fact from the reference material above."
            )

        return "\n\n".join(parts)
