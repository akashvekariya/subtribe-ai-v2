"""Scoring module for candidate evaluation.

Contains the hierarchical scoring algorithm that calculates
skill, category, dimension, and composite scores.
"""

from subtribe_ai.scoring.candidate_scoring import (
    score_candidate,
    ScoringConfig,
)

__all__ = [
    "score_candidate",
    "ScoringConfig",
]
