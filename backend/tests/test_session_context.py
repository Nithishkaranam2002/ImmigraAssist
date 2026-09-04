from app.services.session_context import (
    SessionHistory,
    ac21_completeness_hints,
    expand_query_for_retrieval,
    is_follow_up_query,
    is_forms_follow_up_query,
    is_new_topic_query,
    is_portability_query,
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


def test_job_change_is_treated_as_portability():
    assert is_portability_query("Can the H-1B worker change employers under AC21?")
    assert not is_portability_query("What evidence is required for AC21?")


def test_ac21_query_expands_with_subtopic_context():
    session = SessionHistory(
        text="Q: extension?\nA: ...",
        last_query="Can you explain the 180 day extension?",
        last_visa_type="h4",
        turn_count=2,
    )
    expanded = expand_query_for_retrieval("What evidence is required for AC21?", session)
    assert "AC21" in expanded
    assert "H-4 EAD" in expanded
    assert "180 day extension" not in expanded


def test_ac21_portability_does_not_expand_to_h4_ead():
    """H-1B AC21 portability is INA 214(n)/§105, not H-4 EAD §106."""
    session = SessionHistory(
        text="Q: H-1B?\nA: ...",
        last_query="What are H-1B specialty occupation requirements?",
        last_visa_type="h1b",
        turn_count=1,
    )
    query = "Explain AC21 portability for H1B holders"
    assert is_portability_query(query)
    expanded = expand_query_for_retrieval(query, session)
    assert "H-4 EAD" not in expanded
    assert "section 106" not in expanded
    assert "portability" in expanded.lower()
    assert "214(n)" in expanded
    assert query in expanded


def test_new_topic_skips_retrieval_expansion():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    query = "What is the H-1B cap and how does the lottery work?"
    assert expand_query_for_retrieval(query, session, new_topic=True) == query


def test_ac21_portability_completeness_hint_is_not_h4_ead():
    hints = ac21_completeness_hints("Explain AC21 portability for H1B holders")
    joined = " ".join(hints)
    assert hints
    assert "214(n)" in joined
    assert "§105" in joined
    assert "eligibility for H-4 EAD (per retrieved sources)" not in joined
    assert "Do NOT recast this as H-4 EAD" in joined


def test_ac21_evidence_completeness_hint_still_h4_ead():
    hints = ac21_completeness_hints("What evidence is required for AC21?")
    joined = " ".join(hints)
    assert "H-4 EAD" in joined
    assert "§106" in joined
    assert "214(n)" not in joined


def test_prompt_builder_wires_ac21_completeness_hints():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "app/llm/prompt_builder.py").read_text()
    assert "ac21_completeness_hints" in src
