"""
Text utilities for ContextOn.AI OSS.

Shared helpers for normalizing and tokenizing text so that
retrieval, failure learning, and entity resolution all compare
text the same way (punctuation-insensitive, stopword-aware).
"""

import re
from datetime import datetime, timezone


def utc_iso_now() -> str:
    """Return the current UTC time as an ISO-8601 string ending in 'Z'."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# Small English stopword set (kept intentionally minimal)
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for",
    "of", "to", "in", "on", "at", "by", "with", "from", "as", "is",
    "are", "was", "were", "be", "been", "being", "it", "its", "this",
    "that", "these", "those", "i", "we", "you", "they", "he", "she",
    "what", "which", "who", "whom", "whose", "when", "where", "why",
    "how", "do", "does", "did", "can", "could", "will", "would",
    "should", "shall", "may", "might", "must", "has", "have", "had",
    "not", "no", "yes", "so", "too", "very", "about", "into", "over",
    "after", "before", "between", "under", "again", "further", "once",
    "here", "there", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "than",
    "too", "up", "down", "out", "off", "above", "below",
}

# Words that should not be treated as entities even when capitalized
NON_ENTITY_WORDS = {
    "the", "a", "an", "who", "what", "when", "where", "why", "how",
    "which", "whose", "whom", "does", "do", "did", "is", "are", "was",
    "were", "can", "could", "will", "would", "should", "shall", "may",
    "might", "must", "i", "we", "you", "they", "he", "she", "it",
    "this", "that", "these", "those", "please", "tell", "explain",
    "define", "describe", "give", "show", "find", "list", "what's",
}

# Regex to match non-alphanumeric runs (keeps unicode letters)
_PUNCT_RE = re.compile(r"[^\w\s]|_", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """
    Normalize text for comparison: lowercase, strip punctuation,
    collapse whitespace.
    """
    if not text:
        return ""
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def tokenize(text: str, remove_stopwords: bool = True) -> list:
    """
    Split normalized text into tokens.

    Args:
        text: Raw text
        remove_stopwords: Whether to drop stopwords from the result

    Returns:
        List of lowercase, punctuation-free tokens
    """
    tokens = normalize(text).split()
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens


def token_overlap(text_a: str, text_b: str) -> float:
    """
    Jaccard-style overlap between two texts based on non-stopword tokens.

    Returns a score in [0.0, 1.0]:
    - 1.0 if both texts share all meaningful tokens
    - 0.0 if they share none
    """
    a = set(tokenize(text_a))
    b = set(tokenize(text_b))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def shared_tokens(text_a: str, text_b: str) -> set:
    """Return the set of meaningful tokens shared by two texts."""
    return set(tokenize(text_a)) & set(tokenize(text_b))
