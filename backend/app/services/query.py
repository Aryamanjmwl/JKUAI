"""Small, deterministic semester aliases for English/German curriculum search.

This expands search terms only; it never supplies facts or changes the question sent
for answer generation. Other languages and general translation are outside its scope.
"""

import re


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
