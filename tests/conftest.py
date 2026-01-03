"""Pytest configuration and fixtures for subtribe-ai tests."""

import pytest


@pytest.fixture
def sample_resume_text() -> str:
    """Sample resume text for testing."""
    return """
    John Doe
    Software Engineer
    john.doe@email.com | (555) 123-4567

    EXPERIENCE

    Senior Software Engineer at TechCorp
    January 2020 - Present
    - Led development of microservices architecture
    - Managed team of 5 engineers

    Software Engineer at StartupInc
    June 2017 - December 2019
    - Built REST APIs using Python/FastAPI
    - Implemented CI/CD pipelines

    EDUCATION

    B.S. Computer Science
    University of Technology
    2013 - 2017

    SKILLS

    Python, JavaScript, TypeScript, React, FastAPI, PostgreSQL, Docker, AWS
    """


@pytest.fixture
def sample_framework() -> dict:
    """Sample evaluation framework for testing."""
    return {
        "job_context": {
            "title": "Senior Software Engineer",
            "experience_min": 3,
            "experience_max": 7,
        },
        "skill_criteria": {
            "skills": [
                {
                    "skill_id": "python",
                    "name": "Python",
                    "weight": 0.3,
                    "category": "technical",
                },
                {
                    "skill_id": "fastapi",
                    "name": "FastAPI",
                    "weight": 0.2,
                    "category": "technical",
                },
            ],
        },
        "dimension_weights": {
            "technical_fit": 0.4,
            "experience_fit": 0.3,
            "culture_fit": 0.15,
            "growth_potential": 0.15,
        },
    }
