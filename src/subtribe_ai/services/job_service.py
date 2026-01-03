"""Job description parsing service.

Orchestrates JD parsing -> calibration questions generation.
"""

from dataclasses import dataclass
from typing import TypedDict


class JobData(TypedDict, total=False):
    """Input job data for parsing."""
    title: str
    description: str
    positionType: str
    department: str | None
    locationType: str
    experienceMin: int | None
    experienceMax: int | None


class JobService:
    """Service for parsing job descriptions and generating calibration questions.

    Usage:
        service = JobService()
        result = service.parse(job_data)
    """

    def __init__(self, enable_tracing: bool = False):
        """Initialize the job service.

        Args:
            enable_tracing: Whether to enable Langfuse tracing.
        """
        self._enable_tracing = enable_tracing

    def parse(self, job_data: JobData) -> dict:
        """Parse a job description and generate calibration questions.

        Args:
            job_data: Job information including title, description, etc.

        Returns:
            Dict containing roleAnalysis and calibrationQuestions.
        """
        import time
        import uuid

        from subtribe_ai.baml_client import b
        from subtribe_ai.baml_client.types import JobInput

        start = time.time()

        # Create BAML input
        job_input = JobInput(
            title=job_data["title"],
            description=job_data["description"],
            positionType=job_data.get("positionType", "full_time"),
            department=job_data.get("department"),
            locationType=job_data.get("locationType", "remote"),
            experienceMin=job_data.get("experienceMin"),
            experienceMax=job_data.get("experienceMax"),
        )

        # Call BAML
        baml_response = b.ParseJobDescription(job=job_input)

        # Convert to dict
        result = baml_response.model_dump(mode="json")
        result["jobId"] = str(uuid.uuid4())
        result["timing"] = {"seconds": round(time.time() - start, 2)}

        return result
