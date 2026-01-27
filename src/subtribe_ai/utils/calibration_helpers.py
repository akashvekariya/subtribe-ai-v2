"""Helpers for navigating calibration and framework data structures."""


def extract_selected_skill_ids(calibration: dict) -> set[str]:
    """Extract all selected skill IDs from calibration (both mustHave and goodToHave)."""
    skill_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})

    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            if item.get("selected", False):
                skill_ids.add(item.get("id", ""))

    return skill_ids


def extract_framework_skill_ids(framework: dict) -> set[str]:
    """Extract all skill IDs from framework output."""
    skill_ids = set()
    skill_criteria = framework.get("skill_criteria", {})
    for skill in skill_criteria.get("skills", []):
        skill_ids.add(skill.get("skill_id", ""))
    return skill_ids


def extract_selected_tradeoff_ids(calibration: dict) -> set[str]:
    """Extract all answered tradeoff IDs from calibration."""
    tradeoff_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    tradeoffs = cal_summary.get("tradeoffs", {})

    for section_key in ["experience", "roleSpecific"]:
        section = tradeoffs.get(section_key, {})
        for item in section.get("items", []):
            if item.get("answered", False):
                tradeoff_ids.add(item.get("id", ""))

    return tradeoff_ids


def extract_framework_tradeoff_ids(framework: dict) -> set[str]:
    """Extract all tradeoff IDs from framework output."""
    tradeoff_ids = set()
    for tradeoff in framework.get("tradeoff_preferences", []):
        tradeoff_ids.add(tradeoff.get("tradeoff_id", ""))
    return tradeoff_ids


def extract_selected_items(calibration: dict, section_path: list[str]) -> list[str]:
    """Extract selected item values from a nested calibration section.

    Args:
        calibration: Full calibration dict
        section_path: List of keys to traverse, e.g., ["redFlags", "rejectionBehaviors"]

    Returns:
        List of selected item values
    """
    items: list[str] = []
    current = calibration.get("calibrationSummary", {})

    for key in section_path:
        current = current.get(key, {})
        if not current:
            return items

    for item in current.get("items", []):
        if item.get("selected", False):
            items.append(item.get("value", ""))

    return items


def get_calibration_skill_info(calibration: dict, skill_id: str) -> dict | None:
    """Get skill info from calibration by skill_id.

    Returns dict with name, category, source, is_required or None if not found.
    """
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})

    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            if item.get("id", "") == skill_id:
                return {
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "source": item.get("source", "llm"),
                    "is_required": section_key == "mustHave",
                }

    return None


def build_skill_selection_lookup(calibration: dict) -> dict[str, bool]:
    """Build lookup dict mapping skill_id -> selected status."""
    selection_lookup = {}
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})

    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            skill_id = item.get("id", "")
            selection_lookup[skill_id] = item.get("selected", False)

    return selection_lookup


def build_calibration_skill_ids(calibration: dict) -> set[str]:
    """Build set of all skill IDs in calibration (selected or not)."""
    skill_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    skills = cal_summary.get("skills", {})

    for section_key in ["mustHave", "goodToHave"]:
        section = skills.get(section_key, {})
        for item in section.get("items", []):
            skill_ids.add(item.get("id", ""))

    return skill_ids


def build_calibration_tradeoff_ids(calibration: dict) -> set[str]:
    """Build set of all tradeoff IDs in calibration."""
    tradeoff_ids = set()
    cal_summary = calibration.get("calibrationSummary", {})
    tradeoffs = cal_summary.get("tradeoffs", {})

    for section_key in ["experience", "roleSpecific"]:
        section = tradeoffs.get(section_key, {})
        for item in section.get("items", []):
            tradeoff_ids.add(item.get("id", ""))

    return tradeoff_ids
