"""Framework post-processing module.

Validates, normalizes, and enriches LLM-generated evaluation frameworks.
"""

from subtribe_ai.processing.framework.config import (
    DEFAULT_CONFIG,
    PostProcessingConfig,
    PostProcessingResult,
)
from subtribe_ai.processing.framework.pipeline import run_post_processing_pipeline

__all__ = [
    "PostProcessingConfig",
    "PostProcessingResult",
    "DEFAULT_CONFIG",
    "run_post_processing_pipeline",
]
