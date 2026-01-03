"""Custom exception hierarchy for subtribe-ai.

Follows the pattern established in subtribe-backend with dataclass-based
exceptions that include error codes and structured details.
"""

from dataclasses import dataclass, field


@dataclass
class AIError(Exception):
    """Base exception for all subtribe-ai errors.

    Attributes:
        message: Human-readable error message.
        code: Machine-readable error code for programmatic handling.
        details: Additional context about the error.
    """

    message: str
    code: str = "AI_ERROR"
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


@dataclass
class ResumeParsingError(AIError):
    """Error parsing resume PDF.

    Raised when PDF cannot be read, is corrupted, or LLM fails to parse.
    """

    code: str = "RESUME_PARSING_ERROR"


@dataclass
class BAMLError(AIError):
    """Error from BAML/LLM call.

    Raised when the LLM call fails, times out, or returns invalid response.
    """

    code: str = "BAML_ERROR"
    provider: str = ""
    raw_response: str | None = None


@dataclass
class FactExtractionError(AIError):
    """Error extracting facts from resume.

    Raised during Phase 1 of evaluation when deterministic fact
    extraction fails.
    """

    code: str = "FACT_EXTRACTION_ERROR"


@dataclass
class EvaluationError(AIError):
    """Error evaluating candidate.

    Raised during Phase 2 of evaluation when LLM evaluation fails.
    """

    code: str = "EVALUATION_ERROR"


@dataclass
class FrameworkError(AIError):
    """Error creating or validating evaluation framework.

    Raised when framework creation fails or validation detects issues.
    """

    code: str = "FRAMEWORK_ERROR"


@dataclass
class JobParsingError(AIError):
    """Error parsing job description.

    Raised when job description cannot be parsed or calibration
    questions cannot be generated.
    """

    code: str = "JOB_PARSING_ERROR"


@dataclass
class PDFError(AIError):
    """Error processing PDF file.

    Raised for low-level PDF processing errors like link extraction
    or base64 conversion failures.
    """

    code: str = "PDF_ERROR"
