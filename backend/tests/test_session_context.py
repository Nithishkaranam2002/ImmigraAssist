from app.services.session_context import (
    SessionHistory,
    expand_query_for_retrieval,
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
    assert "H-4 EAD" in expanded
    assert "180 day extension" not in expanded


def test_i140_subtopic_expands_in_h4_session():
    session = SessionHistory(
        text="Q: H4 EAD?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4_ead",
        turn_count=1,
    )
    expanded = expand_query_for_retrieval("What about I-140 evidence?", session)
    assert "H-4 EAD" in expanded
    assert "I-140" in expanded


def test_i140_follow_up_does_not_poison_asylum_session():
    """Asylum → I-140 must not inject H-4 EAD into the retrieval query.

    chat._prepare_query_context builds MetadataFilter from the expanded
    retrieval query; H-4 EAD wording would force the wrong visa corpus.
    """
    session = SessionHistory(
        text="Q: asylum?\nA: ...",
        last_query="What are asylum eligibility requirements?",
        last_visa_type="asylum",
        turn_count=1,
    )
    expanded = expand_query_for_retrieval("What about Form I-140?", session)
    assert "H-4 EAD" not in expanded
    assert "H-1B AC21" not in expanded
    # Still inherits prior topic for retrieval, without visa-poisoning prefixes.
    assert "asylum eligibility" in expanded
    assert "I-140" in expanded


def test_i140_follow_up_does_not_poison_eb2_session():
    session = SessionHistory(
        text="Q: EB-2?\nA: ...",
        last_query="What are EB-2 requirements?",
        last_visa_type="eb2",
        turn_count=1,
    )
    expanded = expand_query_for_retrieval("What about I-140 evidence?", session)
    assert "H-4 EAD" not in expanded
    assert "EB-2 requirements" in expanded


def test_portability_does_not_poison_unrelated_session():
    session = SessionHistory(
        text="Q: green card?\nA: ...",
        last_query="How does adjustment of status work?",
        last_visa_type="green_card",
        turn_count=1,
    )
    expanded = expand_query_for_retrieval("What is portability?", session)
    assert "H-1B AC21 portability" not in expanded


def test_new_topic_skips_retrieval_expansion():
    session = SessionHistory(
        text="Q: H4?\nA: ...",
        last_query="What are H4 EAD requirements?",
        last_visa_type="h4",
        turn_count=1,
    )
    query = "What is the H-1B cap and how does the lottery work?"
    assert expand_query_for_retrieval(query, session, new_topic=True) == query
