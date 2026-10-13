"""I-751 / conditional-residence questions must not inherit the prior visa corpus."""

from pathlib import Path

from app.services.session_context import (
    SessionHistory,
    expand_query_for_retrieval,
    is_conditional_residence_query,
    is_new_topic_query,
)


def _h1b_session() -> SessionHistory:
    return SessionHistory(
        text="Q: cap\nA: ...",
        last_query="What is the H-1B cap and how does the lottery work?",
        last_visa_type="h1b",
        turn_count=1,
    )


def _assert_drops_prior_visa(query: str, session: SessionHistory) -> None:
    new_topic = is_new_topic_query(query, session)
    expanded = expand_query_for_retrieval(query, session, new_topic=new_topic)
    assert new_topic
    assert expanded == query
    assert "H-1B" not in expanded
    assert "lottery" not in expanded


def test_i751_after_h1b_is_new_topic():
    query = "What evidence is required to file Form I-751 for removal of conditions?"
    _assert_drops_prior_visa(query, _h1b_session())


def test_remove_conditions_without_form_number_is_new_topic():
    query = "When must a conditional resident file to remove conditions on residence?"
    _assert_drops_prior_visa(query, _h1b_session())


def test_conditional_permanent_residence_after_l1_is_new_topic():
    session = SessionHistory(
        text="Q: L1?\nA: ...",
        last_query="What is the L-1A maximum period of stay?",
        last_visa_type="l1",
        turn_count=1,
    )
    query = "How does conditional permanent residence end if the petition is late?"
    new_topic = is_new_topic_query(query, session)
    expanded = expand_query_for_retrieval(query, session, new_topic=new_topic)
    assert new_topic
    assert expanded == query
    assert "L-1A" not in expanded


def test_i751_follow_up_does_not_keep_prior_h1b_question():
    """A second I-751 turn must not be glued back onto the H-1B question."""
    session = SessionHistory(
        text="Q: I-751\nA: ...",
        last_query="What evidence is required to file Form I-751?",
        last_visa_type="h1b",
        turn_count=2,
    )
    query = "Does the conditional resident need a joint interview for that I-751?"
    _assert_drops_prior_visa(query, session)


def test_ordinary_follow_up_still_inherits_prior_visa():
    session = _h1b_session()
    query = "What forms are needed for that?"
    assert not is_conditional_residence_query(query)
    assert not is_new_topic_query(query, session)
    expanded = expand_query_for_retrieval(query, session, new_topic=False)
    assert "H-1B" in expanded
    assert query in expanded


def test_removal_proceedings_are_not_conditional_residence():
    """Grounds of removal stay out of this matcher (CourtListener / topic PRs own them)."""
    assert not is_conditional_residence_query(
        "What are the grounds of removal for a criminal conviction?"
    )
    assert not is_conditional_residence_query("Explain cancellation of removal.")
    assert not is_conditional_residence_query(
        "What are the H-1B specialty occupation requirements?"
    )
    assert is_conditional_residence_query("File Form I-751.")
    assert is_conditional_residence_query("Petition to remove conditions on residence.")


def test_matter_visa_override_skips_conditional_residence():
    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "routes" / "chat.py"
    ).read_text()
    assert source.count("is_conditional_residence_query(clean_query)") >= 2
