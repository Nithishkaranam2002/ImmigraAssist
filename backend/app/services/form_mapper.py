VISA_FORMS: dict[str, list[dict[str, str]]] = {
    "h1b": [
        {"form": "I-129", "name": "Petition for Nonimmigrant Worker (cap-subject)"},
        {"form": "G-28", "name": "Notice of Entry of Appearance as Attorney"},
        {"form": "I-797", "name": "Notice of Action"},
    ],
    "h4": [
        {"form": "I-539", "name": "Application to Extend/Change Status"},
        {"form": "I-765", "name": "Application for Employment Authorization"},
    ],
    "h4_ead": [
        {"form": "I-765", "name": "Application for Employment Authorization (EAD)"},
        {"form": "I-539", "name": "Application to Extend/Change Status"},
    ],
    "l1": [
        {"form": "I-129", "name": "Petition for L-1 Intracompany Transferee"},
    ],
    "o1": [
        {"form": "I-129", "name": "Petition for O-1 Extraordinary Ability"},
    ],
    "eb1": [{"form": "I-140", "name": "Immigrant Petition for Alien Worker"}],
    "eb2": [{"form": "I-140", "name": "Immigrant Petition for Alien Worker"}],
    "asylum": [
        {"form": "I-589", "name": "Application for Asylum"},
        {"form": "I-765", "name": "EAD (if eligible)"},
    ],
    "green_card": [
        {"form": "I-485", "name": "Application to Register Permanent Residence"},
        {"form": "I-693", "name": "Report of Medical Examination"},
    ],
    "f1": [
        {"form": "I-20", "name": "Certificate of Eligibility (SEVIS)"},
        {"form": "I-765", "name": "OPT Employment Authorization"},
    ],
}


def get_forms_for_visa(visa_type: str | None) -> list[dict[str, str]]:
    if not visa_type:
        return []
    return VISA_FORMS.get(visa_type.lower(), [])
