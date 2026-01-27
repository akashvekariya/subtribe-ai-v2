"""Configuration for framework post-processing."""

from dataclasses import dataclass, field


@dataclass
class PostProcessingConfig:
    """Configurable thresholds for post-processing.

    All values are configurable - no magic numbers in the code.
    """
    # Completeness thresholds
    missing_error_threshold_pct: float = 30.0  # Error if missing > this %

    # ID matching thresholds
    id_match_similarity_threshold: float = 0.6  # Min similarity for ID fuzzy match

    # Text matching thresholds (for challenges, milestones, constraints)
    text_match_similarity_threshold: float = 0.7  # Min similarity for text fuzzy match

    # Weight divergence threshold
    weight_divergence_threshold_pct: float = 20.0  # Warn if LLM diverges > this %

    # Selection multipliers
    selected_multiplier: float = 1.0  # Multiplier for selected items
    unselected_multiplier: float = 0.3  # Multiplier for unselected items

    # Default weights for missing items
    default_weight_custom: int = 4  # Default weight for custom items (higher priority)
    default_weight_llm: int = 3  # Default weight for LLM-suggested items


@dataclass
class PostProcessingResult:
    """Result of post-processing pipeline."""
    framework: dict
    metadata: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    requires_human_review: bool = False


DEFAULT_CONFIG = PostProcessingConfig()
