"""Post-processing modules for subtribe-ai.

Contains deterministic post-processing logic that enriches LLM outputs
with calculated values (dates, durations, experience totals).
"""

from subtribe_ai.processing.evaluation import (
    EvaluationConfig,
    run_evaluation_pipeline,
)
from subtribe_ai.processing.fact_processor import (
    enriched_facts_to_json,
    run_fact_post_processing,
)
from subtribe_ai.processing.framework import (
    PostProcessingConfig,
    PostProcessingResult,
    run_post_processing_pipeline,
)
from subtribe_ai.processing.resume_processor import (
    process_resume,
)

__all__ = [
    # Fact processing
    "run_fact_post_processing",
    "enriched_facts_to_json",
    # Framework processing
    "run_post_processing_pipeline",
    "PostProcessingResult",
    "PostProcessingConfig",
    # Evaluation processing
    "run_evaluation_pipeline",
    "EvaluationConfig",
    # Resume processing
    "process_resume",
]
