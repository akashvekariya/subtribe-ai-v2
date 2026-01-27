"""Candidate evaluation service.

Evaluates parsed resume JSON against evaluation framework.
"""

import copy
import json
import time
from typing import Any, cast, TypedDict


def _strip_pii_for_evaluation(parsed_resume: dict) -> dict:
    """Remove unnecessary PII fields before sending to LLM.

    Strips fields that don't affect evaluation but could introduce
    bias or non-determinism:
    - full_name, first_name, last_name
    - email, phone
    - linkedin_url, github_url, portfolio_url, other_links
    - timing (parsing time metadata)
    - All warnings (date_warnings, etc.) to avoid evaluation bias

    Keeps location as it may be relevant for remote/onsite evaluation.
    """
    resume = copy.deepcopy(parsed_resume)

    if "personal_info" in resume:
        pi = resume["personal_info"]
        # Keep only location
        resume["personal_info"] = {
            "location": pi.get("location"),
        }

    # Remove timing metadata from parsing
    if "timing" in resume:
        del resume["timing"]

    # Remove warnings from experience (could bias evaluation)
    if "experience" in resume and isinstance(resume["experience"], dict):
        # Remove summary warnings
        if "summary" in resume["experience"]:
            resume["experience"]["summary"].pop("warnings", None)
        # Remove date_warnings from each entry
        for entry in resume["experience"].get("entries", []):
            entry.pop("date_warnings", None)

    # Remove warnings from projects
    if "projects" in resume and isinstance(resume["projects"], dict):
        for entry in resume["projects"].get("entries", []):
            entry.pop("date_warnings", None)

    return resume


def _serialize_deterministic(data: Any) -> str:
    """Serialize dict to JSON with consistent key ordering.

    Uses sort_keys=True to ensure same dict always produces
    same JSON string, regardless of insertion order.
    """
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)


class EvaluationResult(TypedDict, total=False):
    """Result from candidate evaluation.

    Structure mirrors POC evaluation pipeline output:
    - scores: final_score, tier, dimension_scores, etc.
    - manipulation_check: detected, details
    - red_flags: flags list and summary
    - blockers: list of blocking issues
    - can_proceed: whether candidate passes initial screening
    - analysis: skill_analysis, constraint_analysis, tradeoff_analysis, source_summary
    - evaluation: experience_entries, skill_matches, constraint_results, etc.
    - warnings: list of post-processing warnings
    - timing: evaluation timing info
    """
    scores: dict
    manipulation_check: dict
    red_flags: dict
    blockers: list
    can_proceed: bool
    analysis: dict
    evaluation: dict
    warnings: list
    timing: dict


class EvaluationService:
    """Service for evaluating candidates against evaluation frameworks.

    Usage:
        service = EvaluationService()
        result = service.evaluate(parsed_resume, framework)
    """

    def __init__(self, enable_tracing: bool = False):
        """Initialize the evaluation service.

        Args:
            enable_tracing: Whether to enable Langfuse tracing.
        """
        self._enable_tracing = enable_tracing

    def evaluate(self, parsed_resume: dict, framework: dict) -> EvaluationResult:
        """Evaluate a parsed candidate resume against an evaluation framework.

        Args:
            parsed_resume: Parsed resume JSON from ParseResume.
            framework: Evaluation framework from FrameworkService.

        Returns:
            EvaluationResult with scores, matches, and assessments.
        """
        from subtribe_ai.baml_client import b
        from subtribe_ai.processing.evaluation import run_evaluation_pipeline

        total_start = time.time()

        # Strip PII/metadata and serialize with consistent ordering for determinism
        clean_resume = _strip_pii_for_evaluation(parsed_resume)
        framework_json = _serialize_deterministic(framework)
        parsed_resume_json = _serialize_deterministic(clean_resume)

        # Call BAML evaluation
        eval_start = time.time()
        baml_response = b.EvaluateCandidate(
            framework_json=framework_json,
            parsed_resume_json=parsed_resume_json,
        )
        eval_time = time.time() - eval_start

        # Convert to dict
        evaluation_dict = baml_response.model_dump(mode="json")

        # Run scoring post-processing
        result = run_evaluation_pipeline(
            evaluation=evaluation_dict,
            framework=framework,
        )

        # Add timing
        result["timing"] = {
            "evaluation_seconds": round(eval_time, 2),
            "total_seconds": round(time.time() - total_start, 2),
        }

        return cast(EvaluationResult, result)
