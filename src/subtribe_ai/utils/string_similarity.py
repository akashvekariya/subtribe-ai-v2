"""String similarity utilities using Levenshtein distance.

CPU-only implementation with no external dependencies.
"""


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio (0.0 to 1.0) between two strings.

    Higher value means more similar.
    """
    if not s1 or not s2:
        return 0.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    distance = levenshtein_distance(s1.lower(), s2.lower())
    return 1.0 - (distance / max_len)


def find_best_match(
    target_id: str,
    candidate_ids: list[str],
    threshold: float
) -> tuple[str | None, float]:
    """Find best matching ID from candidates using similarity ratio.

    Returns:
        Tuple of (best_match, similarity_score) or (None, 0) if no match above threshold.
    """
    best_match = None
    best_score = 0.0

    for candidate in candidate_ids:
        score = similarity_ratio(target_id, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= threshold:
        return best_match, best_score
    return None, 0.0


def fuzzy_text_match(
    expected_items: set[str],
    found_items: set[str],
    threshold: float
) -> list[str]:
    """Find items from expected set that don't have a fuzzy match in found set.

    Returns:
        List of missing items (items in expected but not matched in found).
    """
    missing = []
    for exp in expected_items:
        found = False
        for fnd in found_items:
            if similarity_ratio(exp, fnd) >= threshold:
                found = True
                break
        if not found:
            missing.append(exp)
    return missing
