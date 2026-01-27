"""Enrichment and sanitization for evaluation output.

Adds human-readable names and removes internal fields for frontend.
"""

from typing import Any

from subtribe_ai.processing.evaluation.config import EvaluationConfig


def enrich_evaluation(
    evaluation: dict,
    framework: dict,
    config: EvaluationConfig
) -> dict[str, Any]:
    """Enrich evaluation with human-readable names from framework.

    Modifies evaluation in place. Returns enrichment stats.
    """
    framework_skills = framework.get("skill_criteria", {}).get("skills", [])
    skill_lookup = {s.get("skill_id", ""): s.get("name", "") for s in framework_skills}
    skill_dealbreaker = {
        s.get("skill_id", ""): s.get("is_dealbreaker", False)
        for s in framework_skills
    }
    tradeoff_lookup = {
        t.get("tradeoff_id", ""): t.get("title", "")
        for t in framework.get("tradeoff_preferences", [])
    }
    constraints = framework.get("hard_constraints", [])
    dim_lookup = {
        d.get("dimension", ""): d.get("dimension", "").replace("_", " ").title()
        for d in framework.get("dimension_weights", [])
    }

    # Enrich skill_matches
    for m in evaluation.get("skill_matches", []):
        sid = m.get("skill_id", "")
        m["skill_name"] = skill_lookup.get(sid, sid)
        source_info = config.source_scores.get(m.get("source_type", "keyword_only"), ("listed", 0.35))
        m["signal_strength"] = source_info[0]
        m["is_dealbreaker"] = skill_dealbreaker.get(sid, False)

    # Enrich tradeoff_signals
    for s in evaluation.get("tradeoff_signals", []):
        s["tradeoff_title"] = tradeoff_lookup.get(
            s.get("tradeoff_id", ""),
            s.get("tradeoff_id", "")
        )

    # Enrich constraint_results
    for r in evaluation.get("constraint_results", []):
        idx = r.get("constraint_idx", -1)
        if 0 <= idx < len(constraints):
            r["constraint_text"] = (
                constraints[idx].get("description", "") or
                constraints[idx].get("original_text", "")
            )

    # Enrich dimension_assessments
    for a in evaluation.get("dimension_assessments", []):
        a["dimension_label"] = dim_lookup.get(
            a.get("dimension", ""),
            a.get("dimension", "").replace("_", " ").title()
        )

    # Enrich experience_entries
    for e in evaluation.get("experience_entries", []):
        e["skills_demonstrated_names"] = [
            skill_lookup.get(sid, sid)
            for sid in e.get("skills_demonstrated", [])
        ]

    return {"enriched": True}


def _remove_empty_values(obj: Any) -> Any:
    """Recursively remove None values and empty collections."""
    if isinstance(obj, dict):
        return {
            k: _remove_empty_values(v)
            for k, v in obj.items()
            if v is not None and v != [] and v != {}
        }
    elif isinstance(obj, list):
        return [_remove_empty_values(item) for item in obj if item is not None]
    return obj


def sanitize_for_frontend(result: dict) -> dict:
    """Remove internal fields before sending to frontend.

    This is the final step before returning evaluation results.
    Removes IDs, internal flags, and simplifies data.
    """
    # Remove metadata
    if "metadata" in result:
        del result["metadata"]

    # Clean up skills section
    if "skills" in result:
        skills = result["skills"]
        # Simplify missing skills list
        if "missing" in skills:
            skills["missing"] = [
                {
                    "skill_name": s.get("skill_name", ""),
                    "category": s.get("category", ""),
                    "is_dealbreaker": s.get("is_dealbreaker", False)
                }
                for s in skills.get("missing", [])
            ]
        # Clean up skill matches
        if "matches" in skills:
            skills["matches"] = [
                {k: v for k, v in m.items() if k not in ("_reconciled", "skill_id")}
                for m in skills.get("matches", []) if m.get("skill_name")
            ]

    # Clean up constraints section
    if "constraints" in result and "results" in result["constraints"]:
        result["constraints"]["results"] = [
            {k: v for k, v in c.items() if k != "constraint_idx"}
            for c in result["constraints"].get("results", []) if c.get("constraint_text")
        ]

    # Clean up tradeoffs section
    if "tradeoffs" in result and "signals" in result["tradeoffs"]:
        result["tradeoffs"]["signals"] = [
            {k: v for k, v in s.items() if k != "tradeoff_id"}
            for s in result["tradeoffs"].get("signals", []) if s.get("tradeoff_title")
        ]

    # Clean up experience entries
    if "experience" in result and "entries" in result["experience"]:
        for e in result["experience"].get("entries", []):
            e.pop("skills_demonstrated", None)

    # Clean up warnings
    if "warnings" in result:
        for w in result["warnings"]:
            w.pop("skills_added", None)

    return _remove_empty_values(result)
