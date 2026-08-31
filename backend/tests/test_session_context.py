from app.services.session_context import (
    SessionHistory,
    expand_query_for_retrieval,
    is_distinct_topic_query,
    is_follow_up_query,
    is_forms_follow_up_query,
    is_new_topic_query,
)


def test_follow_up_detection_with_deictic():
    assert is_follow_up_query(
        "What forms are needed for that?",
        has_prior_turns=True,
    )


def test_follow_up_detection_clarifying_question():
    assert is_follow_up_query(
        "Can you explain the 180 day extension?",
        has_prior_turns=True,
    )


def test_follow_up_expands_with_prior_query():
    session = SessionHistory(
        text="Q: H4 EAD?\nA: ...",
        last_query="What are the requirements for H4 EAD eligibility?",
        last_visa_type="h4",
        turn_count=1,
    )
    expanded = expand_query_for_retrieval("What forms are needed for that?", session)
    assert "H4 EAD eligibility" in expanded
    assert "What forms are needed for that?" in expanded


def test_standalone_query_not_follow_up():
    assert not is_follow_up_query(
        "What is the H-1B cap and how does the lottery work?",
        has_prior_turns=True,
    )


def test_new_topic_when_visa_changes():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    assert is_new_topic_query("What is the H-1B cap and how does the lottery work?", session)


def test_same_topic_follow_up_not_new():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    assert not is_new_topic_query("What forms are needed for that?", session)


def test_forms_follow_up_detection():
    assert is_forms_follow_up_query("What forms are needed for that?")
    assert not is_forms_follow_up_query("What evidence is required for AC21?")


def test_ac21_query_expands_with_subtopic_context():
    session = SessionHistory(
        text="Q: extension?\nA: ...",
        last_query="Can you explain the 180 day extension?",
        last_visa_type="h4",
        turn_count=2,
    )
    expanded = expand_query_for_retrieval("What evidence is required for AC21?", session)
    assert "AC21" in expanded
    assert "180 day extension" not in expanded


def test_new_topic_skips_retrieval_expansion():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    query = "What is the H-1B cap and how does the lottery work?"
    assert expand_query_for_retrieval(query, session, new_topic=True) == query


def test_n400_is_distinct_from_visa_matter():
    """H-1B matter + N-400 must not inherit the matter visa filter."""
    assert is_distinct_topic_query("What is the N-400 naturalization process?")
    assert is_distinct_topic_query(
        "Describe the naturalization physical presence requirements."
    )
    assert is_distinct_topic_query("Explain the PERM labor certification process.")
    assert is_distinct_topic_query("Is the client eligible for TPS or DACA?")


def test_matter_client_questions_are_not_distinct_topics():
    """Visaless questions about the active matter should still inherit its visa."""
    assert not is_distinct_topic_query("What documents are required for this client?")
    assert not is_distinct_topic_query("What forms need to be filed?")
    assert not is_distinct_topic_query("What are the eligibility requirements?")
    assert not is_distinct_topic_query("Explain AC21 portability for H1B holders.")


def test_chat_matter_override_is_gated_on_distinct_topics():
    """Both non-stream and stream pipelines must skip matter visa on N-400/PERM."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "api"
        / "v1"
        / "routes"
        / "chat.py"
    ).read_text()
    assert source.count("is_distinct_topic_query(clean_query)") >= 2
