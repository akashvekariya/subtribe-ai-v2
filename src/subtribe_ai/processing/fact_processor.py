"""
Fact Post-Processing Pipeline

Converts BAML extraction output to tool input, calls tools, produces enriched output.

Pipeline:
1. Convert BAML types -> Tool input types (RawExperienceInput, etc.)
2. Call DateParser -> EnrichedExperience entries
3. Call ExperienceCalculator -> ExperienceSummary
4. Package into EnrichedFacts for Phase 2
"""

from datetime import date
from typing import Optional

from subtribe_ai.utils import (
    CertificationEntry,
    DateParser,
    EducationEntry,
    EnrichedFacts,
    ExperienceCalculator,
    ExperienceType,
    RawDateInput,
    RawExperienceInput,
)


def run_fact_post_processing(
    baml_output,  # ExtractedResumeFacts from BAML
    reference_date: Optional[date] = None,
) -> EnrichedFacts:
    """
    Post-process BAML extraction output into enriched facts.

    Args:
        baml_output: ExtractedResumeFacts from BAML ExtractResumeFacts call
        reference_date: Reference date for "ongoing" calculations (default: today)

    Returns:
        EnrichedFacts ready for Phase 2 evaluation
    """
    ref_date = reference_date or date.today()

    # Step 1: Convert BAML experience entries to tool input
    raw_experiences = _convert_experience_entries(baml_output.experience_entries)

    # Step 2: Parse dates and calculate durations
    parser = DateParser(reference_date=ref_date)
    enriched_experiences = parser.process_experiences(raw_experiences)

    # Step 3: Calculate aggregated summary
    calculator = ExperienceCalculator(reference_date=ref_date)
    experience_summary = calculator.calculate_summary(enriched_experiences)

    # Step 4: Convert education and certifications
    education = _convert_education(baml_output.education_entries)
    certifications = _convert_certifications(baml_output.certifications)

    # Step 5: Calculate years since graduation
    years_since_graduation = _calculate_years_since_graduation(education, ref_date)

    return EnrichedFacts(
        experience=experience_summary,
        education=education,
        certifications=certifications,
        skill_keywords=baml_output.skill_keywords or [],
        years_since_graduation=years_since_graduation,
    )


def _convert_experience_entries(baml_entries: list) -> list[RawExperienceInput]:
    """Convert BAML RawExperienceEntry to tool RawExperienceInput."""
    result = []

    for entry in baml_entries:
        # Convert start_date
        start_date = None
        if entry.start_date:
            start_date = RawDateInput(
                year=entry.start_date.year,
                month=entry.start_date.month,
                is_estimated=entry.start_date.is_estimated,
            )

        # Convert end_date
        end_date = None
        if entry.end_date:
            end_date = RawDateInput(
                year=entry.end_date.year,
                month=entry.end_date.month,
                is_estimated=entry.end_date.is_estimated,
            )

        # Map experience type
        exp_type = _map_experience_type(entry.experience_type)

        raw = RawExperienceInput(
            company=entry.company,
            title=entry.title,
            location=entry.location,
            experience_type=exp_type,
            start_date=start_date,
            end_date=end_date,
            is_ongoing=entry.is_ongoing,
            duration_stated=entry.duration_stated,
            key_contributions=entry.key_contributions or [],
            skills_demonstrated=entry.skills_demonstrated or [],
        )
        result.append(raw)

    return result


def _map_experience_type(baml_type) -> ExperienceType:
    """Map BAML RawExperienceType to tool ExperienceType."""
    # Handle both enum and string
    type_str = baml_type.value if hasattr(baml_type, "value") else str(baml_type)
    type_str = type_str.lower()

    mapping = {
        "full_time": ExperienceType.FULL_TIME,
        "internship": ExperienceType.INTERNSHIP,
        "freelance": ExperienceType.FREELANCE,
        "contract": ExperienceType.CONTRACT,
        "part_time": ExperienceType.PART_TIME,
        "startup_founder": ExperienceType.STARTUP_FOUNDER,
        "academic_project": ExperienceType.ACADEMIC_PROJECT,
        "personal_project": ExperienceType.PERSONAL_PROJECT,
    }

    return mapping.get(type_str, ExperienceType.FULL_TIME)


def _convert_education(baml_entries: list) -> list[EducationEntry]:
    """Convert BAML RawEducationEntry to tool EducationEntry."""
    return [
        EducationEntry(
            institution=e.institution,
            degree=e.degree,
            field_of_study=e.field_of_study,
            graduation_year=e.graduation_year,
            graduation_month=e.graduation_month,
            grade=e.grade,
            is_current=e.is_current,
        )
        for e in baml_entries
    ]


def _convert_certifications(baml_entries: list) -> list[CertificationEntry]:
    """Convert BAML RawCertificationEntry to tool CertificationEntry."""
    return [
        CertificationEntry(
            name=c.name,
            issuer=c.issuer,
            year=c.year,
            month=c.month,
        )
        for c in baml_entries
    ]


def _calculate_years_since_graduation(
    education: list[EducationEntry],
    reference_date: date,
) -> Optional[float]:
    """Calculate years since most recent graduation."""
    completed = [e for e in education if not e.is_current and e.graduation_year]

    if not completed:
        return None

    most_recent = max(
        completed,
        key=lambda e: (e.graduation_year or 0, e.graduation_month or 6),
    )

    grad_year = most_recent.graduation_year
    if grad_year is None:
        return None

    grad_month = most_recent.graduation_month or 6
    grad_date = date(grad_year, grad_month, 1)

    years = (reference_date - grad_date).days / 365.25
    return round(years, 1)


def enriched_facts_to_json(facts: EnrichedFacts) -> dict:
    """
    Convert EnrichedFacts to JSON dict for passing to Phase 2.

    This is the "computed facts" injected into the evaluation prompt.
    """
    exp = facts.experience

    return {
        "experience": {
            "total_months": exp.total_months,
            "total_years": exp.total_years,
            "by_type": {
                "full_time_months": exp.full_time_months,
                "internship_months": exp.internship_months,
                "freelance_months": exp.freelance_months,
                "contract_months": exp.contract_months,
                "part_time_months": exp.part_time_months,
                "startup_months": exp.startup_months,
                "project_months": exp.project_months,
            },
            "has_overlaps": exp.has_overlaps,
            "overlap_months": exp.overlap_months,
            "has_significant_gaps": exp.has_significant_gaps,
            "gaps": [
                {
                    "after": g.after_company,
                    "before": g.before_company,
                    "months": g.gap_months,
                    "significant": g.is_significant,
                }
                for g in exp.gaps
            ],
            "anomalies": exp.anomalies,
            "entries": [
                {
                    "company": e.company,
                    "title": e.title,
                    "location": e.location,
                    "type": e.experience_type.value,
                    "start_date": e.start_date.isoformat() if e.start_date else None,
                    "end_date": e.end_date.isoformat() if e.end_date else None,
                    "is_ongoing": e.is_ongoing,
                    "duration_months": e.duration_months,
                    "start_estimated": e.start_estimated,
                    "end_estimated": e.end_estimated,
                    "anomaly": e.anomaly.value if e.anomaly else None,
                    "skills_demonstrated": e.skills_demonstrated,
                }
                for e in exp.entries
            ],
        },
        "education": [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field": e.field_of_study,
                "year": e.graduation_year,
                "grade": e.grade,
            }
            for e in facts.education
        ],
        "certifications": [
            {
                "name": c.name,
                "issuer": c.issuer,
                "year": c.year,
            }
            for c in facts.certifications
        ],
        "skill_keywords": facts.skill_keywords,
        "years_since_graduation": facts.years_since_graduation,
    }
