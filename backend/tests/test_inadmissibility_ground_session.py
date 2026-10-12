"""Session topic switches onto inadmissibility grounds must drop the prior visa."""

from pathlib import Path

from app.services.session_context import (
    SessionHistory,
    expand_query_for_retrieval,
    is_inadmissibility_ground_query,
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
    assert "H4" not in expanded


def test_unlawful_presence_after_h1b_is_new_topic():
    query = (
        "If the beneficiary accrued unlawful presence for more than one year, "
        "does the ten-year bar apply before they can reenter?"
    )
    _assert_drops_prior_visa(query, _h1b_session())


def test_public_charge_after_h1b_is_new_topic():
    query = "Does the public charge ground apply to this beneficiary after the denial?"
    _assert_drops_prior_visa(query, _h1b_session())


def test_extreme_hardship_after_h4_is_new_topic():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are the requirements for H4 EAD eligibility?",
        last_visa_type="h4",
        turn_count=1,
    )
    query = "What evidence shows extreme hardship to a qualifying spouse?"
    _assert_drops_prior_visa(query, session)


def test_ewi_and_provisional_waiver_after_h1b_is_new_topic():
    query = (
        "The client entered without inspection and needs to know "
        "whether a provisional waiver exists."
    )
    _assert_drops_prior_visa(query, _h1b_session())


def test_present_without_admission_after_h1b_is_new_topic():
    query = "Was the beneficiary present without admission or parole for more than a year?"
    _assert_drops_prior_visa(query, _h1b_session())


def test_continued_unlawful_presence_does_not_keep_prior_visa():
    session = SessionHistory(
        text="Q: bars\nA: ...",
        last_query="Does unlawful presence of more than one year trigger a ten-year bar?",
        last_visa_type="h1b",
        turn_count=2,
    )
    query = "What evidence shows the unlawful presence period was under 180 days?"
    _assert_drops_prior_visa(query, session)


def test_forms_follow_up_still_inherits_prior_topic():
    session = _h1b_session()
    query = "What forms are needed for that?"
    assert not is_new_topic_query(query, session)
    expanded = expand_query_for_retrieval(query, session, new_topic=False)
    assert "H-1B cap" in expanded


def test_h1b_extension_follow_up_is_not_an_inadmissibility_topic():
    session = _h1b_session()
    query = "What documents are required for the extension?"
    assert not is_new_topic_query(query, session)


def test_ordinary_visa_questions_are_not_inadmissibility_grounds():
    assert not is_inadmissibility_ground_query("What is the H-1B cap and how does the lottery work?")
    assert not is_inadmissibility_ground_query("What forms are needed for that?")
    assert not is_inadmissibility_ground_query("Explain the financial hardship of a layoff.")
    assert not is_inadmissibility_ground_query("Is a waiver of the H-1B cap available?")
    assert is_inadmissibility_ground_query("The beneficiary has an EWI history.")
    assert is_inadmissibility_ground_query("Does the 3-year bar apply after an overstay?")


def test_matter_visa_override_skips_inadmissibility_grounds():
    """Both chat pipelines must skip the matter visa filter for these questions."""
    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "routes" / "chat.py"
    ).read_text()
    assert source.count("is_inadmissibility_ground_query(clean_query)") >= 2
