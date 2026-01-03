"""Subtribe AI - AI functionality for the Subtribe recruitment platform.

This package provides:
- Resume parsing (PDF and markdown)
- Job description parsing and calibration
- Evaluation framework creation
- Candidate evaluation with scoring

Usage:
    from subtribe_ai import parse_resume, evaluate_candidate

    # Parse a PDF resume
    with open("resume.pdf", "rb") as f:
        result = parse_resume(f.read())

    # Evaluate a candidate
    evaluation = evaluate_candidate(resume_text, framework)
"""

from subtribe_ai.config import configure, get_settings, Settings
from subtribe_ai.exceptions import (
    AIError,
    ResumeParsingError,
    BAMLError,
    FactExtractionError,
    EvaluationError,
    FrameworkError,
    JobParsingError,
    PDFError,
)
from subtribe_ai.services import (
    ResumeService,
    ParsedResume,
    JobService,
    JobData,
    FrameworkService,
    FrameworkResult,
    EvaluationService,
    EvaluationResult,
)

__version__ = "0.1.0"

# Singleton service instances for convenience functions
_resume_service: ResumeService | None = None
_job_service: JobService | None = None
_framework_service: FrameworkService | None = None
_evaluation_service: EvaluationService | None = None


def _get_resume_service() -> ResumeService:
    """Get or create singleton ResumeService."""
    global _resume_service
    if _resume_service is None:
        _resume_service = ResumeService()
    return _resume_service


def _get_job_service() -> JobService:
    """Get or create singleton JobService."""
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service


def _get_framework_service() -> FrameworkService:
    """Get or create singleton FrameworkService."""
    global _framework_service
    if _framework_service is None:
        _framework_service = FrameworkService()
    return _framework_service


def _get_evaluation_service() -> EvaluationService:
    """Get or create singleton EvaluationService."""
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service


# ============================================================================
# Convenience Functions
# ============================================================================


def parse_resume(
    pdf_bytes: bytes,
    link_padding: float = 2.5,
) -> ParsedResume:
    """Parse a PDF resume into structured JSON.

    Args:
        pdf_bytes: Raw PDF file bytes.
        link_padding: Padding around link rectangles for text extraction.

    Returns:
        ParsedResume with structured data and computed metrics.

    Example:
        with open("resume.pdf", "rb") as f:
            result = parse_resume(f.read())
        print(result["personal_info"]["full_name"])
    """
    return _get_resume_service().parse_pdf(pdf_bytes, link_padding)


def parse_resume_markdown(
    markdown_text: str,
    link_mappings: list[dict] | None = None,
) -> ParsedResume:
    """Parse a markdown resume into structured JSON.

    Args:
        markdown_text: Resume text in markdown format.
        link_mappings: Optional list of {display_text, url} dicts.

    Returns:
        ParsedResume with structured data and computed metrics.
    """
    return _get_resume_service().parse_markdown(markdown_text, link_mappings)


def parse_job_description(job_data: JobData) -> dict:
    """Parse a job description and generate calibration questions.

    Args:
        job_data: Job information including title, description, etc.

    Returns:
        Dict containing roleAnalysis and calibrationQuestions.

    Example:
        result = parse_job_description({
            "title": "Senior Software Engineer",
            "description": "Full job description...",
            "positionType": "full_time",
            "locationType": "remote",
        })
    """
    return _get_job_service().parse(job_data)


def create_framework(calibration_response: dict) -> FrameworkResult:
    """Create an evaluation framework from calibration decisions.

    Args:
        calibration_response: Calibration summary with user selections.

    Returns:
        FrameworkResult with framework and post_processing metadata.
    """
    return _get_framework_service().create(calibration_response)


def evaluate_candidate(resume_text: str, framework: dict) -> EvaluationResult:
    """Evaluate a candidate resume against an evaluation framework.

    Two-phase pipeline:
    - Phase 1: Extract facts (dates, experience) deterministically
    - Phase 2: Evaluate with pre-computed facts as ground truth

    Args:
        resume_text: Raw resume text (markdown or plain text).
        framework: Evaluation framework from create_framework().

    Returns:
        EvaluationResult with scores, matches, and computed facts.

    Example:
        evaluation = evaluate_candidate(resume_text, framework)
        print(f"Score: {evaluation['scores']['final_score']}")
        print(f"Tier: {evaluation['scores']['tier']}")
    """
    return _get_evaluation_service().evaluate(resume_text, framework)


def extract_facts(
    resume_text: str,
    skill_ids: list[str] | None = None,
) -> dict:
    """Extract structured facts from a resume.

    Useful for testing fact extraction before full evaluation.

    Args:
        resume_text: Raw resume text (markdown or plain text).
        skill_ids: Optional list of skill IDs to look for.

    Returns:
        Dict with enriched facts and experience summary.
    """
    return _get_evaluation_service().extract_facts(resume_text, skill_ids)


__all__ = [
    # Version
    "__version__",
    # Configuration
    "configure",
    "get_settings",
    "Settings",
    # Exceptions
    "AIError",
    "ResumeParsingError",
    "BAMLError",
    "FactExtractionError",
    "EvaluationError",
    "FrameworkError",
    "JobParsingError",
    "PDFError",
    # Service classes
    "ResumeService",
    "ParsedResume",
    "JobService",
    "JobData",
    "FrameworkService",
    "FrameworkResult",
    "EvaluationService",
    "EvaluationResult",
    # Convenience functions
    "parse_resume",
    "parse_resume_markdown",
    "parse_job_description",
    "create_framework",
    "evaluate_candidate",
    "extract_facts",
]
