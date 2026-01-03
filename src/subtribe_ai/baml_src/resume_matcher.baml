// Resume-Requirement Matcher POC
// Single API call to match all requirements against resume

// Input Classes
class Requirement {
  text string @description("The requirement text")
  priority int @description("Priority level: 1=must-have, 2=important, 3=nice-to-have")
}

class ResumeData {
  work_experience string[] @description("Work experience bullet points")
  projects string[] @description("Project descriptions")
  skills string[] @description("Skills listed")
  education string[] @description("Education background")
}

class MatchInput {
  requirements Requirement[] @description("All job requirements to match")
  resume ResumeData @description("Candidate resume data")
}

// Output Classes
class RequirementMatch {
  requirement_index int @description("Index of the requirement (0-based)")
  score int @description("Match score 0-10 where 0=no match, 10=perfect match")
  matched_section string @description("Which resume section matched: work_experience, projects, skills, education, or none")
  matched_text string @description("The specific text from resume that matched, or empty if no match")
  reason string @description("Brief reason for the score, max 15 words")
}

class MatchResult {
  matches RequirementMatch[] @description("Match result for each requirement")
  overall_score float @description("Overall match percentage 0-100")
  summary string @description("2-3 sentence summary of candidate fit")
  strengths string[] @description("2-3 key strengths")
  gaps string[] @description("2-3 key gaps or missing requirements")
}

// Main Function
function MatchResumeToRequirements(input: MatchInput) -> MatchResult {
  client Gemini2_5FlashLite
  prompt #"
    {{ _.role("system") }}
    You are an expert recruiter evaluating how well a candidate's resume matches job requirements.

    SCORING GUIDE:
    - 10: Perfect match - requirement explicitly met with evidence
    - 8-9: Strong match - requirement clearly met, minor gaps
    - 6-7: Good match - requirement mostly met, some inference needed
    - 4-5: Partial match - some relevant experience but gaps
    - 2-3: Weak match - tangentially related experience only
    - 0-1: No match - requirement not addressed

    MATCHING RULES:
    1. Years of experience: If resume shows X years and requirement asks for Y years, score based on X/Y ratio
    2. Technology match: Exact tech match = high score, similar tech = medium score
    3. Soft skills: Look for evidence in achievements, not just claims
    4. Be generous with inference but strict with scoring

    PRIORITY WEIGHTING for overall_score:
    - Priority 1 (must-have): Weight 3x
    - Priority 2 (important): Weight 2x
    - Priority 3 (nice-to-have): Weight 1x

    {{ ctx.output_format }}

    {{ _.role("user") }}
    REQUIREMENTS TO MATCH:
    {% for req in input.requirements %}
    [{{ loop.index0 }}] (P{{ req.priority }}): {{ req.text }}
    {% endfor %}

    RESUME DATA:

    Work Experience:
    {% for item in input.resume.work_experience %}
    - {{ item }}
    {% endfor %}

    Projects:
    {% for item in input.resume.projects %}
    - {{ item }}
    {% endfor %}

    Skills:
    {% for item in input.resume.skills %}
    - {{ item }}
    {% endfor %}

    Education:
    {% for item in input.resume.education %}
    - {{ item }}
    {% endfor %}
  "#
}

// Test cases
test TestPythonBackendMatch {
  functions [MatchResumeToRequirements]
  args {
    input {
      requirements [
        { text "5+ years of Python backend development experience", priority 1 },
        { text "Experience with distributed systems and microservices", priority 1 },
        { text "PostgreSQL and Redis database expertise", priority 2 },
        { text "Docker and Kubernetes deployment experience", priority 2 },
        { text "Message queue experience with RabbitMQ or Kafka", priority 3 },
        { text "Team leadership and mentoring capabilities", priority 3 }
      ]
      resume {
        work_experience [
          "Led backend development at TechCorp for 6 years using Python and FastAPI",
          "Built real-time data pipeline using Apache Kafka processing 1M events per day",
          "Designed and implemented microservices architecture serving 10K requests per second"
        ]
        projects [
          "Developed distributed caching system using Redis cluster with 99.9% uptime",
          "Created CI/CD pipeline with Docker containers deployed on AWS EKS Kubernetes"
        ]
        skills [
          "Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, Kafka, AWS"
        ]
        education [
          "MS Computer Science from Stanford University"
        ]
      }
    }
  }
}

test TestWeakCandidate {
  functions [MatchResumeToRequirements]
  args {
    input {
      requirements [
        { text "5+ years of Python backend development experience", priority 1 },
        { text "Experience with distributed systems and microservices", priority 1 },
        { text "PostgreSQL and Redis database expertise", priority 2 }
      ]
      resume {
        work_experience [
          "Junior web developer at StartupCo for 2 years using JavaScript and Node.js",
          "Built simple REST APIs using Express.js"
        ]
        projects [
          "Personal portfolio website using React"
        ]
        skills [
          "JavaScript, Node.js, React, MongoDB, HTML, CSS"
        ]
        education [
          "BS Computer Science from State University"
        ]
      }
    }
  }
}
