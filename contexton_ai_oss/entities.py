"""
Entity extraction and alias resolution for ContextOn.AI OSS.

Entities are extracted from conversation text, then resolved against
already-known entities so that aliases like "PM-JAY" and
"Pradhan Mantri Jan Arogya Yojana" map to a single canonical node
instead of polluting the graph with duplicates.
"""

import re
from typing import List, Tuple

from .text_utils import normalize, tokenize, STOPWORDS, NON_ENTITY_WORDS

# Consecutive capitalized tokens, allowing optional lowercase connector
# words between them. Examples:
#   "National Health Authority"
#   "Pradhan Mantri Jan Arogya Yojana"
#   "Ministry of Health and Family Welfare"
_CAP_PHRASE_RE = re.compile(
    r"\b([A-Z][a-zA-Z&'\-]*(?:\s+(?:(?:of|and|the|for|in|on|at|under|with|by|de|van|da)\s+)?[A-Z][a-zA-Z&'\-]*)*)\b"
)

# Acronyms / initialisms, e.g. "NHA", "PM-JAY", "USA"
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}(?:[-&][A-Z]+)*\b")

# Common verbs that should not be treated as entities even when capitalized
_VERB_WORDS = {
    "implements", "implement", "provides", "provide", "covers", "cover",
    "offers", "offer", "includes", "include", "contains", "contain",
    "requires", "require", "supports", "support", "uses", "use", "helps",
    "help", "makes", "make", "gives", "give", "shows", "show", "finds",
    "find", "lists", "list", "explains", "explain", "describes", "describe",
    "defines", "define", "means", "mean", "works", "work", "runs", "run",
    "starts", "start", "stops", "stop", "opens", "open", "closes", "close",
    "creates", "create", "updates", "update", "deletes", "delete", "adds",
    "add", "removes", "remove", "sends", "send", "receives", "receive",
    "returns", "return", "calls", "call", "loads", "load", "saves", "save",
    "resets", "reset", "changes", "change", "needs", "need", "gets", "get",
    "takes", "take", "follows", "follow", "applies", "apply",
}

MAX_ENTITIES = 10

# Words that are too generic to stand alone as an entity even when capitalized
_GENERIC_WORDS = {
    "health", "family", "welfare", "ministry", "authority", "scheme",
    "policy", "program", "programme", "system", "department", "office",
    "government", "national", "state", "central", "public", "private",
}


def extract_entities(text: str) -> List[Tuple[str, str]]:
    """
    Extract named entities from free text.

    Returns a list of (entity_name, entity_type) tuples, deduplicated
    case-insensitively and capped at MAX_ENTITIES.

    Example:
        extract_entities("Who implements PM-JAY? NHA does.")
        # [("PM-JAY", "concept"), ("NHA", "concept")]
    """
    entities: List[Tuple[str, str]] = []

    # Capitalized phrases (proper nouns / named concepts). When a phrase
    # is rejected (starts with a blocked word), rescan from its second
    # token so proper nouns inside it are not lost - e.g. "The Site
    # Reliability Engineering..." still yields "Site Reliability
    # Engineering".
    pos = 0
    while True:
        match = _CAP_PHRASE_RE.search(text, pos)
        if not match:
            break
        entity = match.group(1).strip()
        tokens = [t.lower() for t in entity.split()]
        first = tokens[0] if tokens else ""
        if not entity or len(entity) <= 2 or \
                first in NON_ENTITY_WORDS or first in _VERB_WORDS or \
                (len(tokens) == 1 and first in _GENERIC_WORDS):
            # Rejected: advance past the first token and rescan
            pos = match.start(1) + len(tokens[0]) if tokens else match.end()
            continue
        entities.append((entity, "concept"))
        pos = match.end()

    # Acronyms / initialisms
    for match in _ACRONYM_RE.finditer(text):
        entity = match.group(0).strip()
        if entity and len(entity) >= 2 and not _inside_longer_entity(entity, entities):
            entities.append((entity, "concept"))

    # Deduplicate (case-insensitive)
    seen = set()
    unique: List[Tuple[str, str]] = []
    for entity, etype in entities:
        key = entity.lower()
        if key not in seen:
            seen.add(key)
            unique.append((entity, etype))
        if len(unique) >= MAX_ENTITIES:
            break

    return unique


def _inside_longer_entity(entity: str, entities: List[Tuple[str, str]]) -> bool:
    """Check whether an acronym is part of an already-extracted phrase."""
    e_lower = entity.lower()
    for name, _ in entities:
        if e_lower in name.lower():
            return True
    return False


def initials(name: str) -> str:
    """
    Compute the initialism of a multi-word name, e.g.
    "Pradhan Mantri Jan Arogya Yojana" -> "pmjay".
    """
    tokens = [t for t in tokenize(name) if t not in STOPWORDS]
    return "".join(t[0] for t in tokens if t).lower()


def _compact(text: str) -> str:
    """Normalize and remove all spaces (for comparing initialisms)."""
    return normalize(text).replace(" ", "")


def _acronym_tokens(text: str) -> List[str]:
    """Return normalized tokens that were all-caps in the original text."""
    return [t.lower() for t in re.findall(r"\b[A-Z]{2,}\b", text)]


def is_alias(candidate: str, existing: str) -> bool:
    """
    Decide whether two names refer to the same entity.

    Rules (checked in order):
    1. Identical after normalization
    2. One is the initialism of the other (PM-JAY vs Pradhan Mantri Jan Arogya Yojana)
    3. An all-caps acronym token of one appears inside the other
       (e.g. "NHA" inside "National Health Authority (NHA)")
    
    SAFETY: Requires minimum 2 chars. For initialism-only matches (no shared
    tokens), we require the longer name to have at least 4 words to prevent
    false positives like "New Home Appliances" matching "NHA".
    """
    a = normalize(candidate)
    b = normalize(existing)

    if not a or not b:
        return False
    if a == b:
        return True

    # SAFETY: Both must be at least 2 chars
    if len(a) < 2 or len(b) < 2:
        return False

    # SAFETY: For short names (< 4 chars), require exact match or shared tokens
    a_tokens = set(a.split()) - STOPWORDS
    b_tokens = set(b.split()) - STOPWORDS
    shared_meaningful = a_tokens & b_tokens
    
    # Initialism match in either direction (space-insensitive)
    a_initials = initials(candidate)
    b_initials = initials(existing)
    
    # Check if the acronym appears as an all-caps token in the original text
    a_has_acronym = bool(re.search(r'\b[A-Z]{2,}\b', candidate))
    b_has_acronym = bool(re.search(r'\b[A-Z]{2,}\b', existing))
    
    # Match if: initials match AND at least one side has the acronym in text
    # For safety, if there are no shared meaningful tokens, require the longer
    # name to have at least 4 words (prevents "New Home Appliances" matching "NHA")
    if a_initials == _compact(existing) and (a_has_acronym or b_has_acronym):
        if shared_meaningful:
            return True
        # Allow if the longer name has at least 4 words
        if max(len(a_tokens), len(b_tokens)) >= 4:
            return True
    if b_initials == _compact(candidate) and (a_has_acronym or b_has_acronym):
        if shared_meaningful:
            return True
        # Allow if the longer name has at least 4 words
        if max(len(a_tokens), len(b_tokens)) >= 4:
            return True

    # Acronym token containment in either direction
    # Only match if the acronym is explicitly in the text (e.g. "NHA" in "National Health Authority (NHA)")
    a_acronym_tokens = _acronym_tokens(candidate)
    b_acronym_tokens = _acronym_tokens(existing)
    
    if a_acronym_tokens and any(t in b_tokens for t in a_acronym_tokens):
        if shared_meaningful:
            return True
    if b_acronym_tokens and any(t in a_tokens for t in b_acronym_tokens):
        if shared_meaningful:
            return True

    return False


def resolve_alias(candidate: str, known: List[str]) -> str:
    """
    Given a candidate name and a list of known entity names, return the
    canonical name the candidate should map to (the candidate itself if
    no alias match is found).
    """
    for name in known:
        if is_alias(candidate, name):
            return name
    return candidate
