"""Summary calculations for evaluation.

Calculates experience, source, and red flag summaries from evaluation data.
"""

from typing import Any


def calculate_experience_summary(experience_entries: list[dict]) -> dict[str, Any]:
    """Calculate total experience from extracted entries.

    LLM extracts each role separately, we sum here to avoid hallucination.

    Returns:
        - total_months: Sum of all experience durations
        - total_years: Rounded years
        - by_type: Breakdown by experience type
        - entries_count: Number of entries
        - has_current_role: Whether candidate is currently employed
    """
    total_months = 0
    by_type: dict[str, dict] = {}
    has_current_role = False

    for entry in experience_entries:
        duration = entry.get("duration_months", 0)
        exp_type = entry.get("experience_type", "other")

        total_months += duration

        if exp_type not in by_type:
            by_type[exp_type] = {"count": 0, "months": 0}
        by_type[exp_type]["count"] += 1
        by_type[exp_type]["months"] += duration

        if entry.get("is_current", False):
            has_current_role = True

    return {
        "total_months": total_months,
        "total_years": round(total_months / 12, 1),
        "by_type": by_type,
        "entries_count": len(experience_entries),
        "has_current_role": has_current_role,
    }


def calculate_source_summary(skill_matches: list[dict]) -> dict[str, Any]:
    """Summarize skill sources and flag potential keyword stuffing."""
    counts = dict.fromkeys(["experience", "project", "education", "inferred", "keyword_only"], 0)

    for match in skill_matches:
        source = match.get("source_type", "keyword_only")
        if source in counts:
            counts[source] += 1

    total = len(skill_matches)
    keyword_only_ratio = counts["keyword_only"] / total if total > 0 else 0

    return {
        "counts": counts,
        "total_skills_matched": total,
        "keyword_only_ratio": round(keyword_only_ratio, 2),
        "keyword_stuffing_flag": keyword_only_ratio > 0.5 and total >= 3,
        "strong_evidence_count": counts["experience"] + counts["project"],
    }


def calculate_red_flag_summary(red_flags: list[dict]) -> dict[str, Any]:
    """Summarize red flags and calculate verification confidence.

    Confidence levels:
    - high: No red flags or only 'info' severity
    - medium: 1-2 'investigate' flags
    - low: 3+ 'investigate' flags OR any 'concern' flags
    """
    if not red_flags:
        return {
            "total_flags": 0,
            "by_severity": {"info": 0, "investigate": 0, "concern": 0},
            "by_type": {},
            "verification_confidence": "high",
            "summary": "No red flags detected",
        }

    by_severity = {"info": 0, "investigate": 0, "concern": 0}
    by_type: dict[str, int] = {}

    for flag in red_flags:
        severity = flag.get("severity", "investigate")
        flag_type = flag.get("flag_type", "unknown")

        if severity in by_severity:
            by_severity[severity] += 1

        if flag_type not in by_type:
            by_type[flag_type] = 0
        by_type[flag_type] += 1

    # Determine confidence level
    if by_severity["concern"] > 0 or by_severity["investigate"] >= 3:
        confidence = "low"
    elif by_severity["investigate"] > 0:
        confidence = "medium"
    else:
        confidence = "high"

    # Generate summary
    parts = []
    if by_severity["concern"] > 0:
        parts.append(f"{by_severity['concern']} concern(s)")
    if by_severity["investigate"] > 0:
        parts.append(f"{by_severity['investigate']} to investigate")
    if by_severity["info"] > 0:
        parts.append(f"{by_severity['info']} info note(s)")
    summary = ", ".join(parts) if parts else "No actionable flags"

    return {
        "total_flags": len(red_flags),
        "by_severity": by_severity,
        "by_type": by_type,
        "verification_confidence": confidence,
        "summary": summary,
    }
