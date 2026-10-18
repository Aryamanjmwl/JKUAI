"""Small, deterministic search aliases for university documents.

This expands search terms only; it never supplies facts or changes the question sent
for answer generation. This glossary is not a general translation service.
"""

import re

# Search vocabulary only: no contacts, rules, credit values, or expected answers.
# Keep expansion out of the embedding and reranking queries: extra generic words
# can dilute the question's meaning, especially its negations and conditions.
_GERMAN_SEARCH_TERMS = (
    (r"\bprerequisites?\b", "Voraussetzung Voraussetzungsprüfung Anmeldevoraussetzungen"),
    (r"\b(?:grades?|assessments?)\b", "Beurteilung Noten Notenauskunft"),
    (r"\bpassed\b", "positiv absolviert bestanden"),
    (r"\b(?:entered|recorded)\b", "eingetragen eingegeben hinterlegt"),
    (r"\bcontact\b", "wenden zuständig"),
    (r"\b(?:exams?|examinations?)\b", "Prüfung Prüfungen"),
    (r"\bparticipants?\b", "Teilnehmer TeilnehmerIn"),
    (r"\bcourses?\b", "Lehrveranstaltung LVA"),
    (r"\b(?:find|search)\b", "Suche suchen"),
    (r"\bregist(?:er|ered|ering|ration)\b", "Anmeldung anmelden"),
    (r"\bwithdraw(?:al)?\b", "Abmeldung abmelden"),
    (r"\b(?:overlaps?|collisions?)\b", "Überschneidung Terminkollision"),
    (r"\btimetable\b", "Stundenplan"),
)


def lexical_query(query: str) -> str:
    """Bridge common English terms to German BM25 tokens without an API call."""
    aliases = [
        terms for pattern, terms in _GERMAN_SEARCH_TERMS if re.search(pattern, query, re.IGNORECASE)
    ]
    expanded = semester_query(query)
    return expanded + (" " + " ".join(aliases) if aliases else "")


def semester_query(query: str) -> str:
    aliases: list[str] = []
    if re.search(r"\b(wintersemester|winter\s+semester|WS)\b", query, re.IGNORECASE):
        aliases.extend(["winter semester", "Wintersemester", "WS"])
    if re.search(r"\b(sommersemester|summer\s+semester|SS)\b", query, re.IGNORECASE):
        aliases.extend(["summer semester", "Sommersemester", "SS"])
    if not aliases and not re.search(r"\bsemester\b", query, re.IGNORECASE):
        return query
    ordinals = [
        (r"first|erst(?:en|es|er|e)?|1\.", "first semester 1. Semester"),
        (r"second|zweit(?:en|es|er|e)?|2\.", "second semester 2. Semester"),
        (r"third|dritt(?:en|es|er|e)?|3\.", "third semester 3. Semester"),
        (r"fourth|viert(?:en|es|er|e)?|4\.", "fourth semester 4. Semester"),
        (r"fifth|fünft(?:en|es|er|e)?|5\.", "fifth semester 5. Semester"),
        (r"sixth|sechst(?:en|es|er|e)?|6\.", "sixth semester 6. Semester"),
    ]
    for pattern, canonical in ordinals:
        if re.search(
            rf"\b(?:{pattern})\s+(?:(?:winter|summer)\s+)?(?:semester|wintersemester|sommersemester)\b",
            query,
            re.IGNORECASE,
        ):
            aliases.append(canonical)
    if re.search(r"\blehrveranstaltungen?\b", query, re.IGNORECASE):
        aliases.append("courses")
    if re.search(r"\bempfohlen\w*\b", query, re.IGNORECASE):
        aliases.append("recommended")
    return query + (" " + " ".join(dict.fromkeys(aliases)) if aliases else "")
