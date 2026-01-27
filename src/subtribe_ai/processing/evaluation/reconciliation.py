"""Skill match reconciliation.

Catches inconsistencies between skills_demonstrated and skill_matches
in LLM evaluation output.
"""

from typing import Any


def reconcile_skill_matches(
    evaluation: dict,
    framework_skills: list[dict],
) -> dict[str, Any]:
    """Reconcile skills_demonstrated with skill_matches to catch LLM inconsistencies.

    The LLM sometimes identifies skills in experience entries (skills_demonstrated)
    but fails to create corresponding skill_match entries with detailed evidence.
    This function catches those gaps and creates basic entries.

    Args:
        evaluation: LLM evaluation output (will be modified in place)
        framework_skills: List of skills from framework to validate skill_ids

    Returns:
        Reconciliation stats: {added_count, skills_added, total_demonstrated, total_matched}
    """
    # Build set of valid skill_ids from framework
    valid_skill_ids = {s.get("skill_id", "") for s in framework_skills}

    # Collect all skills from skills_demonstrated across all experience entries
    demonstrated_skills: dict[str, dict] = {}  # skill_id -> best experience entry
    for entry in evaluation.get("experience_entries", []):
        for skill_id in entry.get("skills_demonstrated", []):
            if skill_id not in valid_skill_ids:
                continue  # Skip invalid skill_ids

            # Keep the entry with longest duration or highest seniority
            if skill_id not in demonstrated_skills:
                demonstrated_skills[skill_id] = entry
            else:
                existing_entry = demonstrated_skills[skill_id]
                # Prefer longer duration or senior titles
                if entry.get("duration_months", 0) > existing_entry.get("duration_months", 0):
                    demonstrated_skills[skill_id] = entry

    # Get existing skill_matches
    existing_matches = {m.get("skill_id", "") for m in evaluation.get("skill_matches", [])}

    # Find skills that are demonstrated but not in skill_matches
    missing_skills = set(demonstrated_skills.keys()) - existing_matches

    # Create basic skill_match entries for missing skills
    added_entries = []
    for skill_id in missing_skills:
        entry = demonstrated_skills[skill_id]
        exp_type = entry.get("experience_type", "full_time")

        # Determine source_type based on experience type
        if exp_type in ("personal_project", "academic_project"):
            source_type = "project"
        else:
            source_type = "experience"

        # Build evidence from experience entry
        contributions = entry.get("key_contributions", [])
        contribution_text = "; ".join(contributions[:2]) if contributions else "Demonstrated in experience"

        new_match = {
            "skill_id": skill_id,
            "source_type": source_type,
            "source_reference": entry.get("company", "Unknown"),
            "evidence": f"{contribution_text} [Auto-reconciled]",
            "_reconciled": True,  # Internal flag for debugging
        }
        added_entries.append(new_match)

    # Add to evaluation's skill_matches
    if "skill_matches" not in evaluation:
        evaluation["skill_matches"] = []
    evaluation["skill_matches"].extend(added_entries)

    return {
        "added_count": len(added_entries),
        "skills_added": list(missing_skills),
        "total_demonstrated": len(demonstrated_skills),
        "total_matched_after": len(evaluation["skill_matches"]),
    }
