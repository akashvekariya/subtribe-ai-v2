"""Resume parsing service.

Orchestrates PDF parsing -> BAML extraction -> post-processing.
"""

from typing import TypedDict

from subtribe_ai.utils import extract_links, pdf_to_base64, preprocess_links, links_to_prompt_text


class ParsedResume(TypedDict):
    """Type hint for parsed resume result."""
    markdown: str  # Gemini-extracted markdown from PDF
    personal_info: dict
    experience: list
    education: list
    projects: list
    certifications: list
    skills: dict | None
    computed: dict
    timing: dict | None


class ResumeService:
    """Service for parsing resumes from PDF or markdown.

    Usage:
        service = ResumeService()
        result = service.parse_pdf(pdf_bytes)
        # or
        result = service.parse_markdown(markdown_text, link_mappings)
    """

    def __init__(self, enable_tracing: bool = False):
        """Initialize the resume service.

        Args:
            enable_tracing: Whether to enable Langfuse tracing.
        """
        self._enable_tracing = enable_tracing

    def parse_pdf(self, pdf_bytes: bytes, link_padding: float = 2.5) -> ParsedResume:
        """Parse a PDF resume into structured JSON.

        Args:
            pdf_bytes: Raw PDF file bytes.
            link_padding: Padding around link rectangles for text extraction.

        Returns:
            ParsedResume with structured data and computed metrics.
        """
        import tempfile
        import time
        from pathlib import Path
        import baml_py

        from subtribe_ai.baml_client import b
        from subtribe_ai.processing.resume_processor import process_resume as run_post_processing

        start = time.time()

        # Write bytes to temp file for link extraction
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            temp_path = Path(f.name)

        try:
            # Extract links from PDF
            links = extract_links(temp_path, padding=link_padding)

            # Convert to base64 for LLM
            pdf_base64 = pdf_to_base64(temp_path)
            resume_pdf = baml_py.Pdf.from_base64(pdf_base64)

            # Preprocess links
            preprocessed = preprocess_links(links)
            links_json = links_to_prompt_text(preprocessed)

            # Step 1: Extract PDF to markdown
            markdown_text = b.ExtractResumeToMarkdown(
                resume=resume_pdf,
                links_json=links_json,
            )

            # Step 2: Parse markdown to structured JSON
            baml_response = b.ParseResume(
                resume_markdown=markdown_text,
                extracted_links_text=links_json,
            )

            # Run post-processing
            result = run_post_processing(baml_response)

            # Include the markdown in the result
            result["markdown"] = markdown_text

        finally:
            temp_path.unlink()

        result["timing"] = {"seconds": round(time.time() - start, 2)}
        return result

    def parse_markdown(
        self,
        markdown_text: str,
        link_mappings: list[dict] | None = None,
    ) -> ParsedResume:
        """Parse a markdown resume into structured JSON.

        Args:
            markdown_text: Resume text in markdown format.
            link_mappings: Optional list of {display_text, url} dicts for link context.

        Returns:
            ParsedResume with structured data and computed metrics.
        """
        import time

        from subtribe_ai.baml_client import b
        from subtribe_ai.processing.resume_processor import process_resume as run_post_processing

        start = time.time()

        # Preprocess links if provided
        if link_mappings:
            preprocessed = preprocess_links(link_mappings)
            extracted_links_text = links_to_prompt_text(preprocessed)
        else:
            extracted_links_text = "No links provided."

        # Call BAML
        baml_response = b.ParseResume(
            resume_markdown=markdown_text,
            extracted_links_text=extracted_links_text,
        )

        # Run post-processing
        result = run_post_processing(baml_response)
        result["markdown"] = markdown_text
        result["timing"] = {"seconds": round(time.time() - start, 2)}

        return result
