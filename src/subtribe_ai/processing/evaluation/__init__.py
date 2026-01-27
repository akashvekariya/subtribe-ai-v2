"""Evaluation post-processing module.

Scores, enriches, and sanitizes LLM-generated candidate evaluations.
"""

from subtribe_ai.processing.evaluation.config import (
    DEFAULT_CONFIG,
    EvaluationConfig,
    ScoringResult,
)
from subtribe_ai.processing.evaluation.pipeline import run_evaluation_pipeline

__all__ = [
    "EvaluationConfig",
    "ScoringResult",
    "DEFAULT_CONFIG",
    "run_evaluation_pipeline",
]
