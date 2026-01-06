# subtribe-ai

AI functionality for the Subtribe recruitment platform.

## Installation

```bash
# Install from git
pip install "subtribe-ai @ git+https://github.com/subtribe/subtribe-ai.git@v0.1.0"

# Or for development
git clone https://github.com/subtribe/subtribe-ai.git
cd subtribe-ai
pip install -e ".[dev]"
```

## Configuration

Set environment variables with the `SUBTRIBE_AI_` prefix:

```bash
export GOOGLE_API_KEY=your-gemini-api-key
```

See `.env.example` for all available options.

## Usage

### Convenience Functions

```python
from subtribe_ai import parse_resume, evaluate_candidate

# Parse a PDF resume
with open("resume.pdf", "rb") as f:
    result = await parse_resume(f.read())

print(result["personal_info"]["full_name"])
print(result["experience_summary"]["total_months"])

# Evaluate a candidate
evaluation = await evaluate_candidate(
    resume_text=resume_markdown,
    framework=evaluation_framework,
)
print(f"Score: {evaluation['scores']['final_score']}")
print(f"Tier: {evaluation['tier']}")
```

### Service Classes

For more control, use the service classes directly:

```python
from subtribe_ai import ResumeService, EvaluationService

# Custom configuration
resume_service = ResumeService(enable_tracing=True)
result = await resume_service.parse(pdf_bytes)

evaluation_service = EvaluationService()
result = await evaluation_service.evaluate(resume_text, framework)
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Generate BAML client
baml generate

# Run tests
pytest

# Lint and format
ruff check src/
ruff format src/
```

## License

MIT
