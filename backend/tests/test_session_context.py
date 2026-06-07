from app.services.session_context import (
    SessionHistory,
    expand_query_for_retrieval,
    is_follow_up_query,
)


def test_follow_up_detection_with_deictic():
    assert is_follow_up_query(
        "What forms are needed for that?",
        has_prior_turns=True,
    )


def test_follow_up_expands_with_prior_query():
    session = SessionHistory(
        text="Q: H4 EAD?\nA: ...",
        last_query="What are the requirements for H4 EAD eligibility?",
        last_visa_type="h4",
    )
    expanded = expand_query_for_retrieval("What forms are needed for that?", session)
    assert "H4 EAD eligibility" in expanded
    assert "What forms are needed for that?" in expanded


def test_standalone_query_not_follow_up():
    assert not is_follow_up_query(
        "What is the H-1B cap and how does the lottery work?",
        has_prior_turns=True,
    )
