# subtribe-ai

The AI engine behind Subtribe, an applicant tracking system for small and mid-size recruiting teams. It turns a resume and a job description into a structured, explainable candidate evaluation.

Packaged as a Python library and consumed by [subtribe-backend](https://github.com/akashvekariya/subtribe-backend-v2).

## How it works

Two pipelines meet at one evaluation step:

```
Resume (PDF/image) -> Markdown -> structured profile ----+
                                                         +--> Evaluation: score, tier, evidence
Job description -> calibration -> evaluation framework --+
```

- **Resume parsing**: extracts the resume verbatim to Markdown (links recovered from the PDF), then to typed JSON. Experience totals, gaps and overlaps are computed in code, not by the model.
- **Job calibration**: reads a job description, asks the recruiter a short set of calibration questions, and builds a weighted evaluation framework from the answers.
- **Evaluation**: scores each candidate against the framework dimension by dimension, with skill matches, hard constraints, red flags and suggested interview questions.
- **Guardrails**: prompt-injection and resume-manipulation checks, enum normalization and weight validation around every model call.

## Stack

- BAML for typed, schema-checked LLM output
- Gemini 2.5 Flash Lite and Gemini 3 Flash
- PyMuPDF for PDF and link extraction
- Pydantic models, Langfuse tracing

## Usage

```python
from subtribe_ai import parse_resume, evaluate_candidate

resume = parse_resume(pdf_bytes)               # {"markdown": ..., "parsed": {...}}
result = evaluate_candidate(resume["parsed"], framework)
print(result["scores"]["final_score"], result["scores"]["tier"])
```

## Development

```bash
pip install -e ".[dev]"
baml-cli generate
pytest
```

Requires `GOOGLE_API_KEY` in the environment.

## Layout

```
src/subtribe_ai/
  baml_src/     prompts and output schemas
  processing/   resume, framework and evaluation pipelines
  services/     public service classes
  utils/        dates, experience math, PDF and link helpers
```
