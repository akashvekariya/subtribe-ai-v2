"""PDF processing utilities for extracting links and text from resume PDFs."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Iterable, List, TypedDict
from urllib.parse import urlparse

import fitz


class LinkEntry(TypedDict):
    """Structure for each extracted hyperlink."""
    display_text: str
    url: str


# Character translation table for cleaning text
TRANSLATION_TABLE = str.maketrans({ch: " " for ch in "\t\n\r•◦▪▫—–"})


def clean_text(text: str) -> str:
    """Compress whitespace, drop artifacts, and keep ASCII-only text."""
    ascii_text = text.translate(TRANSLATION_TABLE).encode("ascii", errors="ignore").decode()
    return " ".join(ascii_text.split())


def pdf_to_base64(pdf_path: Path | str) -> str:
    """Return PDF contents encoded as a base64 ASCII string."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _expand_rect(rect: fitz.Rect, padding: float) -> fitz.Rect:
    """Return a rectangle padded by `padding` points."""
    return fitz.Rect(rect.x0 - padding, rect.y0 - padding, rect.x1 + padding, rect.y1 + padding)


def _iter_uri_links(page: fitz.Page) -> Iterable[tuple[fitz.Rect, str]]:
    """Yield URI link rectangles for the provided page."""
    for link in page.get_links():
        if link.get("kind") != fitz.LINK_URI:
            continue
        uri = link.get("uri")
        rect = link.get("from")
        if not uri or not rect:
            continue
        yield fitz.Rect(rect), uri


def _normalize_url(url: str) -> str:
    """Strip leading mailto: scheme from email hyperlinks."""
    if url.lower().startswith("mailto:"):
        return url.split(":", 1)[1]
    return url


def _fallback_from_url(url: str) -> str:
    """Construct a reasonable label if no text is found."""
    parsed = urlparse(url)
    target = parsed.netloc or parsed.path
    target = target.rstrip("/")
    if target.startswith("www."):
        target = target[4:]
    if not target:
        return url
    return target.split("/")[0]


def _is_url_like(text: str) -> bool:
    """Check if text looks like a URL (contains domain patterns).

    Note: Email addresses are NOT considered URL-like.
    """
    # Emails should not be treated as URL-like
    if '@' in text:
        return False

    url_indicators = ['.com', '.ai', '.so', '.io', '.org', '.me', '.net', '.edu', 'www.', '/', 'http', '.dev']
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in url_indicators)


def _extract_site_name(url_text: str) -> str:
    """Extract and title-case the site name from a URL or domain.

    Examples:
        'linkedin.com' -> 'LinkedIn'
        'hello.ai' -> 'Hello'
        'github.com/user' -> 'GitHub'
        'www.notion.so' -> 'Notion'
    """
    # Remove protocol if present
    cleaned = url_text.lower()
    for prefix in ['https://', 'http://', 'www.']:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]

    # Extract domain (before first slash)
    domain = cleaned.split('/')[0]

    # Get the site name (before first dot or the whole thing)
    site_name = domain.split('.')[0]

    # Title case the result
    return site_name.title() if site_name else url_text


def _display_text(page: fitz.Page, rect: fitz.Rect, padding: float) -> str:
    """Extract the best-effort display text for a hyperlink."""
    for pad in (0.0, padding, padding * 1.5):
        clip = rect if pad == 0 else _expand_rect(rect, pad)
        words = page.get_text("words", clip=clip) or []
        if words:
            words.sort(key=lambda item: (item[5], item[6], item[7]))
            text = " ".join(word[4] for word in words)
            cleaned = clean_text(text)
            if cleaned:
                return cleaned
        raw = page.get_text("text", clip=clip) or ""
        cleaned = clean_text(raw)
        if cleaned:
            return cleaned
    return ""


def extract_links(pdf_path: Path | str, padding: float = 2.0) -> List[LinkEntry]:
    """Extract hyperlinks from a PDF with best-effort display text mapping.

    Deduplicates links by URL, selecting the best display text:
    - Prefers non-URL-like text (e.g., "LinkedIn Profile" over "linkedin.com")
    - Among non-URL-like options, keeps the longest (most descriptive)
    - Converts URL-like text to site name (e.g., "linkedin.com" -> "LinkedIn")

    Args:
        pdf_path: Path to PDF file
        padding: Padding around link rectangles for text extraction

    Returns:
        List of LinkEntry dicts with display_text and url
    """
    path = Path(pdf_path).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    # Collect all (url, label) pairs
    url_labels: dict[str, list[str]] = {}

    with fitz.open(path) as document:
        for page in document:
            for rect, raw_url in _iter_uri_links(page):
                url = _normalize_url(raw_url)
                label = _display_text(page, rect, padding)
                if not label:
                    label = clean_text(_fallback_from_url(url))

                if url not in url_labels:
                    url_labels[url] = []
                url_labels[url].append(label)

    # Select best display text for each URL
    results: List[LinkEntry] = []
    for url, labels in url_labels.items():
        # Separate URL-like and non-URL-like labels
        non_url_labels = [lbl for lbl in labels if not _is_url_like(lbl)]

        if non_url_labels:
            # Prefer non-URL-like text, pick longest (most descriptive)
            best_label = max(non_url_labels, key=len)
        else:
            # All labels are URL-like, convert to site name
            best_label = _extract_site_name(labels[0])

        results.append({"display_text": best_label, "url": url})

    return results
