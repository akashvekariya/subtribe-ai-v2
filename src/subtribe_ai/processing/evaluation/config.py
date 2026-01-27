"""Configuration for evaluation post-processing."""

from dataclasses import dataclass, field


@dataclass
class EvaluationConfig:
    """Configurable scoring parameters."""
    # Source type score mappings (source_type -> (label, multiplier))
    source_scores: dict = field(default_factory=lambda: {
        "experience": ("strong", 0.95),
        "project": ("demonstrated", 0.80),
        "education": ("academic", 0.70),
        "inferred": ("contextual", 0.60),
        "keyword_only": ("listed", 0.35),
    })

    # Dimension level to numeric score mapping
    level_scores: dict = field(default_factory=lambda: {
        "strong": 9.5,
        "good": 7.5,
        "moderate": 5.5,
        "weak": 3.5,
        "poor": 1.5,
    })

    # Constraint type penalties on failure
    # Note: Dealbreaker no longer zeros score - we flag separately
    constraint_penalties: dict = field(default_factory=lambda: {
        "dealbreaker": 0.7,      # 30% penalty but preserves score signal
        "required_day1": 0.85,   # 15% penalty
        "acceptable_gap": 0.95,  # 5% penalty
    })

    # Manipulation attempt penalty
    manipulation_penalty: float = 0.7  # 30% reduction if manipulation detected

    # Tradeoff alignment importance weights
    importance_weights: dict = field(default_factory=lambda: {
        "high": 1.0,
        "medium": 0.6,
        "low": 0.3,
    })

    # Tier thresholds (score ranges)
    tier_thresholds: dict = field(default_factory=lambda: {
        "strong_match": 8.5,
        "good_match": 7.0,
        "moderate_match": 5.5,
        "weak_match": 4.0,
    })


DEFAULT_CONFIG = EvaluationConfig()


@dataclass
class ScoringResult:
    """Final scoring result."""
    dimension_scores: dict
    final_score: float
    tier: str
    is_dealbreaker: bool
    skill_analysis: dict
    constraint_analysis: dict
    tradeoff_analysis: dict
    metadata: dict = field(default_factory=dict)
