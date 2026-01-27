"""
Link Pre-processor

Prepares PDF-extracted links before sending to LLM:
- Derives GitHub profile URL from repo URLs
- Derives other profile URLs where possible
- Marks link types for LLM context
"""

import re
from typing import Any, Mapping, Optional, Sequence


def extract_github_username(url: str) -> Optional[str]:
    """Extract GitHub username from any GitHub URL."""
    match = re.match(r"https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)", url)
    if match:
        username = match.group(1)
        # Exclude GitHub reserved paths
        reserved = {"features", "enterprise", "pricing", "login", "join", "explore", "topics", "collections", "sponsors"}
        if username.lower() not in reserved:
            return username
    return None


def is_github_profile_url(url: str) -> bool:
    """Check if URL is a GitHub profile (not a repo)."""
    return bool(re.match(r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?$", url))


def is_github_repo_url(url: str) -> bool:
    """Check if URL is a GitHub repo."""
    return bool(re.match(r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+", url))


def preprocess_links(link_mappings: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """
    Preprocess links before sending to LLM.

    - If GitHub repo URLs exist but no profile URL, derive and add profile URL
    - Add _link_type hint for clearer LLM matching

    Args:
        link_mappings: List of {"display_text": "...", "url": "..."} dicts

    Returns:
        Enriched list with derived links and type hints
    """
    result = []
    github_usernames = set()
    has_github_profile = False

    # First pass: collect info and copy links with type hints
    for link in link_mappings:
        url = link.get("url", "").strip()
        display = link.get("display_text", "").strip()

        enriched = {
            "display_text": display,
            "url": url,
        }

        # Check for GitHub profile
        if is_github_profile_url(url):
            has_github_profile = True
            enriched["_type"] = "github_profile"
            username = extract_github_username(url)
            if username:
                github_usernames.add(username)

        # Check for GitHub repo and extract username
        elif is_github_repo_url(url):
            enriched["_type"] = "github_repo"
            username = extract_github_username(url)
            if username:
                github_usernames.add(username)

        # Check for other known patterns
        elif "linkedin.com/in/" in url:
            enriched["_type"] = "linkedin"
        elif "kaggle.com/" in url:
            enriched["_type"] = "kaggle"
        elif "@" in url or "mailto:" in url:
            enriched["_type"] = "email"
        elif any(d in url for d in [".netlify.app", ".vercel.app", ".streamlit.app", ".herokuapp.com", ".github.io"]):
            enriched["_type"] = "demo"

        result.append(enriched)

    # Second pass: derive GitHub profile if missing
    if not has_github_profile and github_usernames:
        # Use the first username found (they should all be the same for one person)
        username = list(github_usernames)[0]
        derived_profile = {
            "display_text": f"[Derived from repos]",
            "url": f"https://github.com/{username}",
            "_type": "github_profile",
            "_derived": True,
        }
        # Insert at beginning for visibility
        result.insert(0, derived_profile)

    return result


def links_to_prompt_text(preprocessed_links: list[dict]) -> str:
    """
    Format preprocessed links for inclusion in LLM prompt.

    Groups by type for easier matching.
    """
    if not preprocessed_links:
        return "No links extracted from PDF."

    lines = []

    # Separate by type
    profiles = []
    repos = []
    demos = []
    others = []

    for link in preprocessed_links:
        link_type = link.get("_type", "")
        if link_type in ["github_profile", "linkedin", "kaggle", "email"]:
            profiles.append(link)
        elif link_type == "github_repo":
            repos.append(link)
        elif link_type == "demo":
            demos.append(link)
        else:
            others.append(link)

    # Profile links
    if profiles:
        lines.append("PROFILE LINKS (assign to personal_info fields):")
        for link in profiles:
            derived = " [derived]" if link.get("_derived") else ""
            lines.append(f"  - {link['url']}{derived}")
            if link["display_text"] and not link.get("_derived"):
                lines.append(f"    display: \"{link['display_text']}\"")
        lines.append("")

    # GitHub repos
    if repos:
        lines.append("PROJECT REPO LINKS (match repo name to project name):")
        for link in repos:
            # Extract repo name from URL for hint
            match = re.search(r"github\.com/[^/]+/([^/]+)", link["url"])
            repo_name = match.group(1) if match else ""
            lines.append(f"  - {link['url']}")
            lines.append(f"    repo_name: \"{repo_name}\", display: \"{link['display_text']}\"")
        lines.append("")

    # Demo links
    if demos:
        lines.append("DEMO LINKS (match to projects):")
        for link in demos:
            lines.append(f"  - {link['url']}")
            lines.append(f"    display: \"{link['display_text']}\"")
        lines.append("")

    # Other links
    if others:
        lines.append("OTHER LINKS:")
        for link in others:
            lines.append(f"  - {link['url']}")
            lines.append(f"    display: \"{link['display_text']}\"")
        lines.append("")

    return "\n".join(lines)
