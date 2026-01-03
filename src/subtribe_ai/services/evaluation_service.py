"""Candidate evaluation service.

Orchestrates the two-phase evaluation pipeline:
- Phase 1: Deterministic fact extraction
- Phase 2: LLM evaluation with pre-computed facts
"""

from typing import TypedDict


class EvaluationResult(TypedDict):
    """Result from candidate evaluation."""
    scores: dict
    skill_matches: list
    dimension_assessments: list
    constraint_results: list
    summary: dict
    computed_facts: dict
    timing: dict


class EvaluationService:
    """Service for evaluating candidates against evaluation frameworks.

    Usage:
        service = EvaluationService()
        result = service.evaluate(resume_text, framework)
    """

    def __init__(self, enable_tracing: bool = False):
        """Initialize the evaluation service.

        Args:
            enable_tracing: Whether to enable Langfuse tracing.
        """
        self._enable_tracing = enable_tracing

    def evaluate(self, resume_text: str, framework: dict) -> EvaluationResult:
        """Evaluate a candidate resume against an evaluation framework.

        Two-phase pipeline:
        - Phase 1: Extract facts (dates, experience) with deterministic tools
        - Phase 2: Evaluate with pre-computed facts as ground truth

        Args:
            resume_text: Raw resume text (markdown or plain text).
            framework: Evaluation framework from FrameworkService.

        Returns:
            EvaluationResult with scores, matches, and computed facts.
        """
        import json
        import time

        from subtribe_ai.baml_client import b
        from subtribe_ai.processing.fact_processor import (
            run_fact_post_processing,
            enriched_facts_to_json,
        )
        from subtribe_ai.processing.evaluation_processor import run_evaluation_pipeline

        total_start = time.time()

        # Extract skill IDs from framework
        skill_ids = [
            s.get("skill_id")
            for s in framework.get("skill_criteria", {}).get("skills", [])
            if s.get("skill_id")
        ]

        # Phase 1: Extract facts with deterministic tools
        phase1_start = time.time()

        # Call BAML for fact extraction
        raw_facts = b.ExtractResumeFacts(
            resume_text=resume_text,
            skill_ids=skill_ids,
        )

        # Post-process facts
        enriched_facts = run_fact_post_processing(raw_facts)
        computed_facts = enriched_facts_to_json(enriched_facts)
        phase1_time = time.time() - phase1_start

        # Phase 2: Evaluate with pre-computed facts
        phase2_start = time.time()
        framework_json = json.dumps(framework, indent=2)
        computed_facts_json = json.dumps(computed_facts, indent=2)

        baml_response = b.EvaluateCandidate(
            framework_json=framework_json,
            candidate_resume=resume_text,
            computed_facts_json=computed_facts_json,
        )

        # Convert to dict
        evaluation_dict = baml_response.model_dump(mode="json")
        phase2_time = time.time() - phase2_start

        # Run scoring post-processing
        result = run_evaluation_pipeline(
            evaluation=evaluation_dict,
            framework=framework,
        )

        # Add computed facts and timing
        result["computed_facts"] = computed_facts
        result["timing"] = {
            "phase1_seconds": round(phase1_time, 2),
            "phase2_seconds": round(phase2_time, 2),
            "total_seconds": round(time.time() - total_start, 2),
        }

        return result

    def extract_facts(self, resume_text: str, skill_ids: list[str] | None = None) -> dict:
        """Extract structured facts from a resume (Phase 1 only).

        Useful for testing fact extraction before full evaluation.

        Args:
            resume_text: Raw resume text (markdown or plain text).
            skill_ids: Optional list of skill IDs to look for.

        Returns:
            Dict with enriched facts and experience summary.
        """
        import time

        from subtribe_ai.baml_client import b
        from subtribe_ai.processing.fact_processor import (
            run_fact_post_processing,
            enriched_facts_to_json,
        )

        start = time.time()

        # Call BAML for fact extraction
        raw_facts = b.ExtractResumeFacts(
            resume_text=resume_text,
            skill_ids=skill_ids or [],
        )

        # Post-process facts
        enriched_facts = run_fact_post_processing(raw_facts)
        result = enriched_facts_to_json(enriched_facts)
        result["timing"] = {"seconds": round(time.time() - start, 2)}

        return result
