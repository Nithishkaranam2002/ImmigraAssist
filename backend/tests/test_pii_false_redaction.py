"""PII regex must not delete legal facts that the sanitizer would rewrite."""
import re

from app.guardrails.pii_detector import PIIDetector

# Same last-pass substitution as OutputSanitizer.sanitize. detect_and_redact
# calls _regex_redact whenever GLiNER is off, which is the default.
_APPLICANT = re.compile(r"\[REDACTED-[A-Z_]+\]")


def _shown(text: str) -> str:
    redacted = PIIDetector()._regex_redact(text).redacted_text
    return _APPLICANT.sub("the applicant", redacted)


def test_priority_date_survives_query_and_answer():
    query = "Is a priority date of 03/15/2019 current for EB-2 India?"
    answer = "A priority date of 03/15/2019 is earlier than the posted cutoff."
    assert _shown(query) == query
    assert _shown(answer) == answer


def test_effective_date_and_rfe_deadline_survive():
    assert "01/17/2017" in _shown("The final rule took effect on 01/17/2017.")
    assert "04/02/2024" in _shown("The RFE deadline is 04/02/2024.")
    assert "the applicant" not in _shown("The final rule took effect on 01/17/2017.")


def test_cap_figures_are_not_zip_codes():
    text = "The H-1B regular cap is 65000 and the master's cap is 20000."
    assert _shown(text) == text


def test_uscis_receipt_tail_is_not_a_phone():
    spaced = "What does receipt IOE 0912345678 mean for this I-140?"
    hyphenated = "Receipt EAC-2390123456 was issued yesterday."
    assert _shown(spaced) == spaced
    assert _shown(hyphenated) == hyphenated


def test_labeled_dates_of_birth_are_still_redacted():
    samples = [
        ("Client DOB 03/15/1990 needs an I-485.", "03/15/1990"),
        ("D.O.B. 4/2/1988 is on the passport.", "4/2/1988"),
        ("The child was born on 1/2/1999.", "1/2/1999"),
        ("Birthday is 7/4/2001.", "7/4/2001"),
        ("03/15/1990 (date of birth)", "03/15/1990"),
    ]
    for text, secret in samples:
        shown = _shown(text)
        assert secret not in shown
        assert "the applicant" in shown
        assert "[REDACTED-" not in shown


def test_real_contact_identifiers_are_still_redacted():
    phone = _shown("Call the client at (415) 555-0199 about the RFE.")
    assert "555-0199" not in phone
    assert "the applicant" in phone

    dashed = _shown("Call 415-555-0199 or +1 (415) 555-0198.")
    assert "415-555-0199" not in dashed
    assert "555-0198" not in dashed

    ssn = _shown("SSN 123-45-6789 should not be stored.")
    assert "123-45-6789" not in ssn

    email = _shown("Email ada@example.com is on the G-28.")
    assert "ada@example.com" not in email

    alien = _shown("A-number A123456789 is on the I-485.")
    assert "A123456789" not in alien

    postal = _shown("Mail the packet to CA 94105, zip code 94105-1234.")
    assert "94105" not in postal
