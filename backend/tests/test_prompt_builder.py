from app.llm.prompt_builder import PromptBuilder
from app.retrieval.context_builder import BuiltContext


def test_prompt_includes_court_decision_context():
    context = BuiltContext(
        context_text=(
            "## RELEVANT LAWS AND POLICIES\n\n"
            "[LAW 1] USCIS Policy Manual\nPolicy text.\n\n"
            "## RELEVANT COURT DECISIONS\n\n"
            "[COURT 1] WashTech v. DHS\nSummary: STEM OPT rule challenge."
        ),
        law_references=[{"index": 1}],
        case_references=[],
        court_case_references=[{"index": 1, "case_name": "WashTech v. DHS"}],
        total_tokens_estimate=25,
    )

    prompt = PromptBuilder().build(
        query="What cases address STEM OPT?",
        context=context,
        visa_type="f1",
    )

    assert "1 court decisions" in prompt.user_message
    assert "## RELEVANT COURT DECISIONS" in prompt.user_message
    assert "[COURT 1] WashTech v. DHS" in prompt.user_message
