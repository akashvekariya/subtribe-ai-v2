"""
Resume Post-Processing Pipeline

Adds computed fields to BAML ParsedResume output:
- Duration calculations from date strings (LLM doesn't do math)
- Experience aggregation (totals, gaps, overlaps)
- Date warnings (vague, missing, inverted, future)
- Years since graduation

BAML output is returned as-is. This only ADDS computed metrics.
"""

import re
from datetime import date
from typing import Any, Optional

from .models import (
    DateWarning,
    ExperienceMetrics,
    ExperienceSummary,
    Gap,
    ProjectMetrics,
)


def parse_date_string(date_str: Optional[str]) -> tuple[Optional[date], bool]:
    """
    Parse date string to date object.
    Returns (date_obj, is_vague) where is_vague=True if year-only.
    """
    if not date_str:
        return None, False

    # YYYY-MM format
    if re.match(r"^\d{4}-\d{2}$", date_str):
        year, month = date_str.split("-")
        return date(int(year), int(month), 1), False

    # YYYY format (year only - vague)
    if re.match(r"^\d{4}$", date_str):
        return date(int(date_str), 6, 1), True  # Mid-year for calculations

    return None, False


def calculate_duration(
    start_str: Optional[str],
    end_str: Optional[str],
    is_ongoing: bool,
    reference_date: date,
) -> tuple[int, list[str]]:
    """
    Calculate duration in months from date strings.
    Returns (duration_months, warnings).
    """
    warnings = []

    start_date, start_vague = parse_date_string(start_str)
    end_date, end_vague = parse_date_string(end_str)

    if start_vague:
        warnings.append(DateWarning.VAGUE_DATE.value)
    if end_vague:
        warnings.append(DateWarning.VAGUE_DATE.value)

    # Handle missing dates
    if start_date is None and end_date is None:
        warnings.append(DateWarning.MISSING_BOTH.value)
        return 0, warnings

    if start_date is None:
        warnings.append(DateWarning.MISSING_START.value)
        return 0, warnings

    # Determine end date
    if is_ongoing or end_date is None:
        end_date = reference_date

    # Check for future dates
    if start_date > reference_date:
        warnings.append(DateWarning.FUTURE_START.value)
        return 0, warnings

    if end_date > reference_date and not is_ongoing:
        warnings.append(DateWarning.FUTURE_END.value)

    # Check for inverted dates
    if end_date < start_date:
        warnings.append(DateWarning.INVERTED.value)
        return 0, warnings

    # Calculate months (inclusive of both start and end month)
    # Oct 2023 - Nov 2023 = 2 months, Oct 2023 - Dec 2023 = 3 months
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    return max(1, months), warnings


def get_enum_value(baml_enum) -> str:
    """Extract string value from BAML enum."""
    if hasattr(baml_enum, "value"):
        return baml_enum.value
    return str(baml_enum)


def compute_experience_metrics(
    experiences: list[Any],
    reference_date: date,
) -> list[ExperienceMetrics]:
    """Compute duration and warnings for each experience."""
    metrics = []
    for i, exp in enumerate(experiences):
        duration, warnings = calculate_duration(
            exp.start_date,
            exp.end_date,
            exp.is_ongoing,
            reference_date,
        )
        metrics.append(ExperienceMetrics(
            index=i,
            duration_months=duration,
            warnings=warnings,
        ))
    return metrics


def detect_overlaps(
    experiences: list[Any],
    metrics: list[ExperienceMetrics],
    reference_date: date,
) -> tuple[bool, int]:
    """Detect overlapping experiences. Returns (has_overlaps, overlap_months)."""
    if len(experiences) < 2:
        return False, 0

    # Build timeline with valid dates
    timeline = []
    for i, exp in enumerate(experiences):
        start_date, _ = parse_date_string(exp.start_date)
        end_date: date | None
        if exp.is_ongoing:
            end_date = reference_date
        else:
            end_date, _ = parse_date_string(exp.end_date)

        if start_date and end_date:
            timeline.append((start_date, end_date, i))

    if len(timeline) < 2:
        return False, 0

    # Sort by start date
    timeline.sort(key=lambda x: x[0])

    total_overlap = 0
    for i in range(len(timeline) - 1):
        _, end1, _ = timeline[i]
        start2, _, _ = timeline[i + 1]

        if end1 > start2:
            overlap = (end1.year - start2.year) * 12 + (end1.month - start2.month)
            total_overlap += max(0, overlap)

    return total_overlap > 0, total_overlap


def detect_gaps(
    experiences: list[Any],
    reference_date: date,
) -> list[Gap]:
    """Detect gaps between experiences. Returns gaps > 3 months."""
    if len(experiences) < 2:
        return []

    # Build timeline
    timeline = []
    for exp in experiences:
        start_date, _ = parse_date_string(exp.start_date)
        end_date: date | None
        if exp.is_ongoing:
            end_date = reference_date
        else:
            end_date, _ = parse_date_string(exp.end_date)

        if start_date and end_date:
            timeline.append((start_date, end_date, exp.company))

    if len(timeline) < 2:
        return []

    # Sort by end date
    timeline.sort(key=lambda x: x[1])

    gaps = []
    for i in range(len(timeline) - 1):
        _, end1, company1 = timeline[i]
        start2, _, company2 = timeline[i + 1]

        if start2 > end1:
            gap_months = (start2.year - end1.year) * 12 + (start2.month - end1.month)
            if gap_months > 3:
                gaps.append(Gap(
                    after_company=company1,
                    before_company=company2,
                    months=gap_months,
                    significant=gap_months >= 6,
                ))

    return gaps


def build_experience_summary(
    experiences: list[Any],
    metrics: list[ExperienceMetrics],
    reference_date: date,
) -> ExperienceSummary:
    """Build aggregated experience summary."""
    if not experiences:
        return ExperienceSummary()

    # Total months
    total_months = sum(m.duration_months for m in metrics)

    # By category
    by_category: dict[str, int] = {}
    for i, exp in enumerate(experiences):
        category = get_enum_value(exp.category)
        by_category[category] = by_category.get(category, 0) + metrics[i].duration_months

    # Overlaps and gaps
    has_overlaps, overlap_months = detect_overlaps(experiences, metrics, reference_date)
    gaps = detect_gaps(experiences, reference_date)

    # Adjust total for overlaps
    adjusted_total = max(0, total_months - overlap_months)

    # Collect all warnings
    all_warnings = []
    for i, m in enumerate(metrics):
        for w in m.warnings:
            warning_str = f"{experiences[i].company}: {w}"
            if warning_str not in all_warnings:
                all_warnings.append(warning_str)

    return ExperienceSummary(
        total_months=adjusted_total,
        by_category=by_category,
        has_overlaps=has_overlaps,
        overlap_months=overlap_months,
        gaps=gaps,
        has_significant_gaps=any(g.significant for g in gaps),
        entry_metrics=metrics,
        warnings=all_warnings,
    )


def compute_project_metrics(
    projects: list[Any],
    reference_date: date,
) -> list[ProjectMetrics]:
    """Compute duration for projects with dates."""
    metrics = []
    for i, proj in enumerate(projects):
        duration = None
        warnings: list[str] = []

        if proj.start_date or proj.end_date:
            duration, warnings = calculate_duration(
                proj.start_date,
                proj.end_date,
                False,
                reference_date,
            )

        metrics.append(ProjectMetrics(
            index=i,
            duration_months=duration,
            warnings=warnings,
        ))
    return metrics


def compute_education_insights(
    education: list[Any],
    reference_date: date,
) -> tuple[Optional[int], Optional[str]]:
    """
    Compute months since graduation and highest education level.
    Returns (months_since_graduation, highest_level).

    Graduation = first completed degree at bachelors level or above.
    High school/diploma/associate don't count as "graduated".
    """
    level_order = ["high_school", "associate", "diploma", "bachelors", "masters", "doctorate"]
    graduation_levels = ["bachelors", "masters", "doctorate"]

    months_since_graduation = None
    highest_level = None
    first_graduation_date = None

    for edu in education:
        level = get_enum_value(edu.level)

        # Track highest COMPLETED level
        if level in level_order and not edu.is_current:
            if highest_level is None or level_order.index(level) > level_order.index(highest_level):
                highest_level = level

        # Find FIRST graduation (bachelors+, completed only)
        if level in graduation_levels and not edu.is_current and edu.end_date:
            grad_date, _ = parse_date_string(edu.end_date)
            if grad_date and grad_date <= reference_date:
                if first_graduation_date is None or grad_date < first_graduation_date:
                    first_graduation_date = grad_date

    # Calculate months since first graduation
    if first_graduation_date:
        months = (reference_date.year - first_graduation_date.year) * 12 + (reference_date.month - first_graduation_date.month)
        months_since_graduation = max(0, months)

    return months_since_graduation, highest_level


def process_resume(baml_output, reference_date: Optional[date] = None) -> dict:
    """
    Main entry point: Add computed fields to BAML ParsedResume.

    Returns dict with consolidated structure:
    - experience: { summary: {...}, entries: [...] }
    - education: { summary: {...}, entries: [...] }
    - projects: { summary: {...}, entries: [...] }
    - Other fields (personal_info, skills, certifications, etc.) unchanged
    """
    if reference_date is None:
        reference_date = date.today()

    # Get base BAML output
    result = baml_output.model_dump(mode="json")

    # Compute experience metrics
    exp_metrics = compute_experience_metrics(baml_output.experience, reference_date)
    exp_summary = build_experience_summary(baml_output.experience, exp_metrics, reference_date)

    # Build experience entries with duration merged in
    experience_entries = []
    for i, exp in enumerate(result.get("experience", [])):
        exp["duration_months"] = exp_metrics[i].duration_months
        exp["date_warnings"] = exp_metrics[i].warnings
        experience_entries.append(exp)

    # Restructure experience
    result["experience"] = {
        "summary": {
            "total_months": exp_summary.total_months,
            "by_category": exp_summary.by_category,
            "has_overlaps": exp_summary.has_overlaps,
            "overlap_months": exp_summary.overlap_months,
            "gaps": [g.model_dump() for g in exp_summary.gaps],
            "has_significant_gaps": exp_summary.has_significant_gaps,
            "warnings": exp_summary.warnings,
        },
        "entries": experience_entries,
    }

    # Compute project metrics
    proj_metrics = compute_project_metrics(baml_output.projects, reference_date)

    # Build project entries with duration merged in
    project_entries = []
    for i, proj in enumerate(result.get("projects", [])):
        proj["duration_months"] = proj_metrics[i].duration_months
        proj["date_warnings"] = proj_metrics[i].warnings
        project_entries.append(proj)

    # Restructure projects
    result["projects"] = {
        "summary": {
            "count": len(project_entries),
        },
        "entries": project_entries,
    }

    # Compute education insights
    months_since_grad, highest_level = compute_education_insights(
        baml_output.education,
        reference_date,
    )

    # Restructure education
    education_entries = result.get("education", [])
    result["education"] = {
        "summary": {
            "highest_level": highest_level,
            "months_since_graduation": months_since_grad,
        },
        "entries": education_entries,
    }

    return result


def resume_to_dict(result: dict) -> dict:
    """Pass-through for compatibility."""
    return result


def resume_to_json(result: dict) -> str:
    """Convert result to JSON string."""
    import json
    return json.dumps(result, indent=2)
