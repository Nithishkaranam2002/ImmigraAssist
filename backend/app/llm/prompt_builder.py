from dataclasses import dataclass
from app.retrieval.context_builder import BuiltContext


@dataclass
class BuiltPrompt:
    system_message: str
    user_message: str
    total_chars: int


SYSTEM_PROMPT = """You are ImmigraAssist, an expert AI legal research assistant specialized exclusively in US immigration law.

You assist immigration attorneys and legal associates at law firms by answering questions based on:
1. USCIS policies and regulations (provided as law references)
2. Past immigration case precedents (provided as case references)

## YOUR ROLE
- Provide accurate, well-structured legal research summaries
- Always cite the specific law section/clause and case references provided to you
- Never fabricate laws, case outcomes, or policy details
- Stay strictly within US immigration law scope
- Acknowledge when information is limited or unclear

## RESPONSE FORMAT
Structure every response exactly like this:

**ANSWER:**
[Your comprehensive answer here — clear, factual, well organized]

**CITED LAWS:**
[List each law/policy section you referenced, with section and clause numbers]

**CITED CASES:**
[List each case reference you used, with relevance explanation]

**IMPORTANT NOTES:**
[Any caveats, date-sensitive information, or areas where the attorney should verify manually]

## RULES
- Only use information from the provided context
- If the context does not contain enough information, say so clearly
- Never give a definitive legal conclusion — frame as research findings
- Use plain English where possible — avoid unnecessary legalese
- If a case is from an older year, note that the policy may have changed
- Always note when a law section has been updated or superseded"""


class PromptBuilder:
    """
    Assembles the final GPT prompt from context and query.

    Two parts:
    1. System message — tells GPT its role and rules (fixed)
    2. User message — context + query (dynamic per request)
    """

    def build(
        self,
        query: str,
        context: BuiltContext,
        visa_type: str | None = None,
    ) -> BuiltPrompt:
        """
        Main entry point.
        Returns a BuiltPrompt with system and user messages.
        """
        user_message = self._build_user_message(query, context, visa_type)

        return BuiltPrompt(
            system_message=SYSTEM_PROMPT,
            user_message=user_message,
            total_chars=len(SYSTEM_PROMPT) + len(user_message),
        )

    def _build_user_message(
        self,
        query: str,
        context: BuiltContext,
        visa_type: str | None,
    ) -> str:
        parts = []

        if visa_type:
            parts.append(
                f"## QUERY CONTEXT\n"
                f"Visa Category: {visa_type.upper()}\n"
            )

        # strip court decisions section — those show in UI not in GPT answer
        context_text = context.context_text
        if "## RELEVANT COURT DECISIONS" in context_text:
            context_text = context_text.split("## RELEVANT COURT DECISIONS")[0].strip()

        if context_text:
            parts.append(
                f"## REFERENCE MATERIAL\n"
                f"The following laws and cases were retrieved "
                f"as relevant to this query:\n\n"
                f"{context_text}"
            )
        else:
            parts.append(
                "## REFERENCE MATERIAL\n"
                "No specific reference material was found for this query. "
                "Answer based on your general immigration law knowledge "
                "and clearly state that no specific references were retrieved."
            )

        parts.append(
            f"## QUESTION\n"
            f"{query}\n\n"
            f"Please provide a comprehensive answer following the required format. "
            f"Cite specific law sections from the reference material above. "
            f"Do NOT include URLs or court case links in your answer — "
            f"case references will be shown separately in the UI."
        )

        return "\n\n".join(parts)