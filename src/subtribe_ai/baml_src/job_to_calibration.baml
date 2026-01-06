// Job Description Parser Schema V3
// Chain-of-thought: Reason first, then generate domain-appropriate content

// ============================================================================
// ENUMS
// ============================================================================

enum SkillCategory {
  Technical @alias("technical")
  Soft @alias("soft")
  Domain @alias("domain")
  Education @alias("education")
  Certification @alias("certification")
  Custom @alias("custom")
}

enum RoleComplexity {
  Junior @alias("junior")
  Mid @alias("mid")
  Senior @alias("senior")
  Lead @alias("lead")
  Executive @alias("executive")
}

enum TradeoffRelevance {
  High @alias("high")
  Medium @alias("medium")
  Low @alias("low")
  NotRelevant @alias("not_relevant")
}

enum RoleFamily {
  SoftwareEngineering @alias("software_engineering") @description("Backend, frontend, fullstack, mobile, embedded software")
  DataAndML @alias("data_ml") @description("Data science, ML/AI, data engineering, analytics")
  DevOpsAndInfra @alias("devops_infra") @description("DevOps, SRE, platform, cloud infrastructure")
  ProductAndBusiness @alias("product_business") @description("Product management, business analysis, strategy")
  DesignAndCreative @alias("design_creative") @description("UX/UI design, graphic design, content, creative")
  HardwareAndPhysical @alias("hardware_physical") @description("Hardware engineering, electrical, mechanical, manufacturing")
  QualityAndTesting @alias("quality_testing") @description("QA, test engineering, reliability")
  SecurityAndCompliance @alias("security_compliance") @description("Security engineering, compliance, risk")
  SalesAndMarketing @alias("sales_marketing") @description("Sales, marketing, growth, partnerships")
  PeopleAndOps @alias("people_ops") @description("HR, recruiting, operations, admin")
  Other @alias("other") @description("Roles that don't fit above categories")
}


// ============================================================================
// CORE CLASSES
// ============================================================================

class ExtractedSkill {
  id string @description("Unique identifier, e.g., 'skill_figma', 'skill_python', 'edu_btech_cs', 'cert_aws_solutions_architect'")
  name string @description("Display name appropriate to the role domain")
  category SkillCategory @description("technical (tools/methods), soft (interpersonal), domain (industry-specific), education (degrees/qualifications), or certification (professional certifications)")
}

class TradeoffOption {
  id string @description("Unique identifier")
  label string @description("Short display label, 2-4 words")
  description string @description("Brief description of this candidate profile, under 15 words")
  implication string @description("What choosing this means. Use 'Upside:' prefix only - positive framing. Max 12 words.")
}

class TradeoffScenario {
  id string @description("Unique identifier")
  title string @description("Scenario title framed for THIS role's domain")
  description string @description("Context for this trade-off based on THIS specific JD and role family")
  options TradeoffOption[] @description("Exactly 2 options representing the trade-off poles")
  relevance TradeoffRelevance @description("How relevant this trade-off is for THIS specific role")
  isRoleSpecific bool @description("true if generated specifically for this role's domain")
}

class PriorityOption {
  id string @description("Unique identifier")
  label string @description("Display label appropriate to role domain")
  hint string @description("One-line context hint, max 8 words")
}

class PsychOption {
  id string @description("Unique identifier")
  label string @description("Option text, under 10 words")
}

class PsychQuestion {
  id string @description("Question identifier")
  question string @description("The question to ask the hiring manager, framed for this role type")
  options PsychOption[] @description("4 options that indirectly reveal hiring priorities for THIS role")
}

// ============================================================================
// RED FLAGS - Role-specific dealbreakers
// ============================================================================

class RedFlagsSection {
  rejectionBehaviors string[] @description("5-6 candidate behaviors that would be automatic rejections for THIS role family")
  trainableGaps string[] @description("4-5 skill gaps the company could reasonably train for THIS role")
  nonTrainableGaps string[] @description("4-5 capabilities that MUST be present on day 1 - cannot be trained")
}

// ============================================================================
// SECTION CLASSES
// ============================================================================

class RoleAnalysis {
  // Chain-of-thought reasoning (OUTPUT FIRST - guides all subsequent generation)
  roleFamily RoleFamily @description("Primary role family this job belongs to")
  reasoning string @description("2-3 paragraph analysis: (1) What is this role really about? (2) What makes someone succeed vs fail? (3) What are the hidden tensions in this JD?")
  assessmentApproach string @description("1 paragraph: How should candidates be evaluated? Portfolio, technical depth, business acumen, communication?")
  keyConflicts string[] @description("2-4 specific conflicts in THIS JD. E.g., 'Senior expertise but startup salary', 'Innovation but maintenance work'")

  // Role metadata
  complexity RoleComplexity @description("Assessed complexity/seniority level")
  domainKeywords string[] @description("3-5 domain-specific keywords from JD")
  roleType string @description("Specific role type, e.g., 'ux_designer', 'backend_engineer', 'product_manager'")
  senioritySignals string[] @description("2-3 key signals indicating seniority level")
}

class SkillRealityCheck {
  mustHaveSkills ExtractedSkill[] @description("15-25 skills absolutely required. Only extract explicitly mentioned skills - no inferred capabilities. Use hybrid format 'Category (Example1/Example2)' when JD lists examples of interchangeable tools.")
  goodToHaveSkills ExtractedSkill[] @description("12-18 skills beneficial but not required. CRITICAL: These must be DIFFERENT from mustHaveSkills - no duplicates or overlaps. Only extract explicitly mentioned skills.")
  instruction string @description("Instruction text for the skill validation UI")
}

class ExperienceTradeoffs {
  scenarios TradeoffScenario[] @description("4-6 trade-off scenarios relevant to THIS role family with relevance scores")
}

class RoleSpecificTradeoffs {
  scenarios TradeoffScenario[] @description("2 trade-offs unique to THIS role's specific domain/function")
  instruction string @description("Instruction for the trade-offs section")
}

class PipelineCalibration {
  assessmentPriorities PriorityOption[] @description("6 options for what to prioritize when assessing candidates - domain-appropriate")
  problemTypes PriorityOption[] @description("4 types of problems/challenges this role will face")
  trajectoryOptions PriorityOption[] @description("4 career growth paths this role could lead to. Use format: '[Track Type]' with hint describing what that means. E.g., 'Senior IC' -> 'Deepen expertise, stay hands-on'. Make role-specific but universally understandable.")
  communicationOptions PriorityOption[] @description("4 work/collaboration styles. Use format: '[Style]' with hint. E.g., 'Heads-Down' -> 'Mostly independent, deep focus'. Must be clear about how collaborative the role is.")
}

class PsychologicalInsights {
  questions PsychQuestion[] @description("3 questions that indirectly reveal hidden hiring priorities for THIS role")
}

class HonestAssessment {
  challengeOptions string[] @description("5 role-specific challenges someone in this role will face")
  growthOptions string[] @description("4 things that would help someone thrive in this role")
  quitRiskOptions string[] @description("4 honest reasons someone might quit this role in 6 months")
}

class Day60Expectations {
  milestones string[] @description("5 specific, measurable 60-day goals appropriate to this role family")
  instruction string @description("Instruction text for the milestones selection UI")
}

// ============================================================================
// MAIN PAYLOAD
// ============================================================================

class CalibrationQuestionsPayload {
  skillRealityCheck SkillRealityCheck @description("Skills extracted and categorized from JD")
  experienceTradeoffs ExperienceTradeoffs @description("Trade-off scenarios relevant to this role")
  roleSpecificTradeoffs RoleSpecificTradeoffs @description("Trade-offs specific to this role's domain")
  redFlags RedFlagsSection @description("Role-specific dealbreakers and gaps")
  pipelineCalibration PipelineCalibration @description("Assessment and pipeline priorities")
  psychologicalInsights PsychologicalInsights @description("Questions revealing hidden priorities")
  honestAssessment HonestAssessment @description("Honest challenges and growth factors")
  day60Expectations Day60Expectations @description("First 60 days success metrics")
}

class JDParseResponse {
  roleAnalysis RoleAnalysis @description("OUTPUT FIRST: Role reasoning and context that guides all outputs")
  calibrationQuestions CalibrationQuestionsPayload @description("All calibration questions and options")
}

// ============================================================================
// INPUT
// ============================================================================

class JobInput {
  title string @description("Job title")
  description string @description("Full job description text")
  positionType string @description("full_time, part_time, contract, internship")
  department string? @description("Department name if provided")
  locationType string @description("remote, onsite, hybrid")
  experienceMin int? @description("Minimum years of experience")
  experienceMax int? @description("Maximum years of experience")
}

// ============================================================================
// MAIN FUNCTION
// ============================================================================

function ParseJobDescription(job: JobInput) -> JDParseResponse {
  client Gemini3FlashPreview__JobToCalibration
  prompt #"
    {{ _.role("system") }}
    You are an expert recruiter and hiring consultant who works across ALL industries and role types - not just software engineering. Your task is to analyze job descriptions and generate calibration questions that help hiring managers make explicit decisions about their REAL requirements.

    ## WHY THIS MATTERS

    Job descriptions are typically aspirational wish lists filled with conflicting requirements. A JD might ask for "10 years of experience" but also want someone "hungry to learn." It might list 15 required skills when only 3 actually matter for success.

    The problem: Hiring managers often don't realize these conflicts exist until they're comparing candidates and making inconsistent decisions. One day they reject a candidate for lacking a specific skill; the next day they hire someone without it because they liked their communication style.

    Your job is to EXPOSE these hidden conflicts and force hiring managers to make explicit trade-off decisions BEFORE they see candidates. This creates:
    1. Consistent evaluation criteria across all candidates
    2. Faster hiring decisions (no debate about what "really" matters)
    3. Better candidate experience (clear expectations)
    4. Reduced bias (decisions made on criteria, not gut feeling)

    ## CRITICAL: ROLE FAMILY AWARENESS

    You MUST first identify the role family and tailor ALL outputs accordingly. Different roles have fundamentally different success criteria:

    **Software Engineering**: Code quality, system design, debugging, technical depth
    **Design & Creative**: Portfolio quality, design thinking, user empathy, craft
    **Product & Business**: Strategic thinking, stakeholder management, data-driven decisions
    **Hardware & Physical**: Hands-on skills, safety awareness, manufacturing knowledge
    **Data & ML**: Statistical rigor, model deployment, data intuition
    **DevOps & Infra**: Reliability mindset, automation, incident response
    **Sales & Marketing**: Revenue impact, relationship building, market awareness
    **People & Ops**: Organizational skills, empathy, process optimization

    DO NOT use software engineering terminology for non-software roles. A designer's "technical skills" are Figma and prototyping, not Python. A product manager's "system design" is product architecture, not distributed systems.

    ## HOW TO ANALYZE

    STEP 1 - ROLE REASONING (Output this FIRST in roleReasoning):
    Before generating ANY calibration content, write 2-3 paragraphs analyzing:
    - What role family does this belong to? What is this role REALLY about?
    - What makes someone succeed vs fail in THIS specific role?
    - What are the hidden tensions or conflicts in this JD?
    - How should candidates for THIS role be evaluated?

    This reasoning will guide ALL subsequent outputs. If your reasoning says "this is a design role focused on user research," then your skills, trade-offs, and red flags should all reflect design/research priorities.

    STEP 2 - IDENTIFY KEY CONFLICTS:
    List 2-4 specific conflicts in THIS JD. Examples:
    - "Wants senior expertise but startup compensation"
    - "Asks for creativity but describes execution-heavy work"
    - "Requires deep specialization but lists 10 different technologies"
    - "Says 'autonomous' but describes heavy process"

    STEP 3 - EXTRACT SKILLS INTELLIGENTLY:

    When extracting skills, decide between UMBRELLA vs SPECIFIC based on substitutability:

    **Use Umbrella Format "Category (Example1/Example2)"** when:
    - JD lists examples in parentheses (e.g., "cloud platforms (AWS, GCP, Azure)")
    - The tools are functionally interchangeable (knowing one means you can learn others)
    - Examples illustrate the category, not define the requirement

    **Use Specific Tool/Framework** when:
    - JD explicitly requires it ("Must have 3+ years PyTorch experience")
    - The tool is NOT substitutable (PyTorch ≠ TensorFlow - different APIs/patterns)
    - Proficiency in one doesn't transfer to alternatives

    **Key principle: Transferability determines umbrella vs separate.**

    **Use SEPARATE skills when:**
    - Each requires fundamentally different training or expertise
    - Proficiency in one doesn't mean proficiency in others
    - They have different workflows, methodologies, or knowledge bases

    **Use UMBRELLA when:**
    - Core concepts and workflows are the same
    - Knowing one means you can quickly adapt to others
    - They serve the same function with minor differences

    Apply this logic to ANY domain - tech, healthcare, legal, finance, manufacturing, etc.
    When JD lists alternatives with "or", decide: same core skill (umbrella) or different expertise (separate)?

    **Quantity:** Extract 15-25 must-have and 12-18 good-to-have skills. Be comprehensive - include technical, soft, domain, education, and certification requirements across all categories. Don't artificially limit extraction.

    **EDUCATION CATEGORY (category: education):**
    Use for formal educational qualifications and degrees. These are credentials, not learnable skills.

    Patterns to extract:
    - Degree levels: Bachelor's, Master's, PhD, Diploma
    - Degree types with field: "[Degree] in [Field]" or "[Field] Background"
    - Equivalent qualifications: "[Degree] or equivalent experience"

    Apply umbrella vs specific logic here too:
    - UMBRELLA: "Engineering Degree (B.Tech/BE/B.Sc)" when multiple degree types accepted
    - SPECIFIC: "MBA" when only that specific degree is mentioned

    Place in mustHaveSkills if JD says "required", "must have", "mandatory".
    Place in goodToHaveSkills if JD says "preferred", "plus", "nice to have".

    **CERTIFICATION CATEGORY (category: certification):**
    Use for professional certifications and formal credentials issued by recognized bodies. These are validated qualifications, not self-learned skills.

    Patterns to extract:
    - Vendor certifications: Cloud providers, software vendors, tool-specific
    - Professional certifications: Industry-recognized credentials for the role domain
    - Methodology certifications: Process/framework certifications relevant to the role

    Apply umbrella vs specific logic here too:
    - UMBRELLA: "Cloud Certification (AWS/GCP/Azure)" when any cloud cert is acceptable
    - SPECIFIC: Extract exact certification name when JD requires a specific one

    Place in mustHaveSkills if JD says "required", "must have", "mandatory".
    Place in goodToHaveSkills if JD says "preferred", "plus", "nice to have".

    **CRITICAL: No Duplicates:** mustHaveSkills and goodToHaveSkills must be completely separate sets. A skill cannot appear in both lists. If a skill is required, it goes in mustHave only. If it's optional, it goes in goodToHave only.

    **CRITICAL: Only extract explicitly mentioned skills.** Do NOT infer or derive skills. If you cannot point to the exact word/phrase in the JD, do not extract it.

    DO extract:
    - Exact terms and named tools/technologies/methods from the JD
    - Explicit requirements stated with action words ("experience with", "proficiency in")
    - Specific qualifications, certifications, or credentials mentioned

    DO NOT extract:
    - Inferred capabilities from context
    - Derived soft skills from job duties
    - Assumed knowledge not explicitly stated
    - Interpreted phrasing (use JD's actual words)
    - Combined non-transferable skills as one (split into separate skills)

    **Use natural phrasing that matches how candidates describe themselves.**
    Extract skills using words candidates would put on their resume, not interpreted versions.

    STEP 4 - DISTINGUISH COMPANY DOMAIN FROM ROLE REQUIREMENTS:

    CRITICAL: Separate what the COMPANY works on from what the CANDIDATE must do.

    - Company domain: The industry, product, or market the company operates in
    - Role requirements: The actual skills, behaviors, and capabilities the candidate needs

    When generating skills, red flags, and assessments:
    - Focus on what the candidate will DO in this role
    - Do NOT require candidates to have domain expertise in the company's product area unless explicitly stated
    - The company's mission describes their business, not the candidate's required background

    A candidate for a technical role at a healthcare company doesn't need healthcare experience unless the JD explicitly requires it. They need the technical skills to build healthcare software.

    A candidate for an ML role at a design company doesn't need design skills. They need ML skills to build systems that process design content.

    Always ask: "Does the JD explicitly require this, or am I inferring it from the company description?"

    STEP 5 - GENERATE DOMAIN-APPROPRIATE CONTENT:
    All subsequent outputs must be consistent with your reasoning.

    ## OUTPUT RULES

    OUTPUT ORDER MATTERS - Generate in this exact sequence:
    1. roleAnalysis.roleReasoning FIRST (chain-of-thought that guides everything)
    2. roleAnalysis fields (complexity, keywords, type, signals)
    3. skillRealityCheck (domain-appropriate skills)
    4. experienceTradeoffs (universal trade-offs with role-specific framing)
    5. roleSpecificTradeoffs (unique to this domain)
    6. redFlags (domain-appropriate dealbreakers)
    7. pipelineCalibration (domain-appropriate assessment criteria)
    8. psychologicalInsights (role-appropriate questions)
    9. honestAssessment (role-specific challenges)
    10. day60Expectations (role-appropriate milestones)

    KEEP TEXT CONCISE:
    - Labels: 2-4 words
    - Descriptions: Under 15 words
    - Implications: Use "Upside:" prefix ONLY - focus on what you gain from each choice. Max 12 words.
    - Hints: Max 8 words

    ## LANGUAGE GUIDELINES

    1. NEVER use "perfect match" or "ideal candidate" - use "strong fit" or "high potential"
    2. Keep copy accessible to non-technical hiring managers
    3. Frame trade-offs positively:
       - Use "Upside:" prefix instead of "Risk:" or "Tradeoff:"
       - Focus on what you gain from each choice
       - Example: "Upside: brings industry expertise" NOT "Risk: may resist new ways"
    4. Psychological questions should be PREFERENCE questions, not interview questions
       - Frame as: "What type of person..." or "Which working style..."
    5. Day 60 milestones should be action-oriented and specific
       - Start with action verbs: "Ship", "Complete", "Establish", "Deliver"
       - Be specific: "Ship first feature to production" not "Get familiar with codebase"

    ## DOMAIN-SPECIFIC GUIDANCE

    For each role family, apply the umbrella vs specific logic appropriately:

    ### For SOFTWARE ENGINEERING roles:
    - Skills: Programming languages (specific: Python, JavaScript), frameworks (umbrella: Cloud Platform (AWS/GCP)), system design, testing
    - Trade-offs: Code quality vs speed, specialist vs generalist, build vs buy
    - Red flags: Cannot explain technical decisions, no code samples, blames others for bugs
    - Assessment: Coding challenges, system design, debugging exercises
    - Day 60: Ship features, fix bugs, understand codebase

    ### For DESIGN & CREATIVE roles:
    - Skills: Design tools (umbrella: Design Software (Figma/Sketch)), prototyping, user research (specific methods), visual design
    - Trade-offs: Pixel-perfect vs speed, user advocacy vs business needs, process vs intuition
    - Red flags: No portfolio, cannot explain design decisions, ignores user feedback
    - Assessment: Portfolio review, design challenge, critique exercise
    - Day 60: Complete design audit, establish design system, ship first feature design

    ### For PRODUCT & BUSINESS roles:
    - Skills: Roadmapping, stakeholder management, data analysis, market research
    - Trade-offs: Data-driven vs intuition, feature depth vs breadth, customer vs business
    - Red flags: Cannot prioritize, avoids hard decisions, no metrics orientation
    - Assessment: Case study, prioritization exercise, stakeholder simulation
    - Day 60: Own a feature area, establish metrics, build stakeholder relationships

    ### For HARDWARE & PHYSICAL roles:
    - Skills: CAD Software (umbrella: CAD Tools (SolidWorks/AutoCAD)), manufacturing processes (specific), safety protocols, testing equipment
    - Trade-offs: Cost vs quality, speed vs reliability, innovation vs proven methods
    - Red flags: Safety shortcuts, cannot troubleshoot hands-on, poor documentation
    - Assessment: Technical drawing review, hands-on demonstration, safety knowledge
    - Day 60: Complete safety training, understand production line, first design review

    ### For DATA & ML roles:
    - Skills: Statistics, Python/R (specific), ML Frameworks (umbrella or specific based on requirement), data pipelines, Visualization Tools (Tableau/PowerBI)
    - Trade-offs: Model accuracy vs interpretability, research vs production, perfect vs good enough
    - Red flags: Cannot explain model choices, ignores data quality, overfits everything
    - Assessment: Data analysis challenge, model explanation, SQL/coding test
    - Day 60: Understand data infrastructure, deliver first analysis, establish metrics

    ### For SALES & MARKETING roles:
    - Skills: CRM Platform (Salesforce/HubSpot), communication, market analysis, campaign management, Marketing Automation (Marketo/Pardot)
    - Trade-offs: Volume vs quality, short-term vs long-term, brand vs performance
    - Red flags: Cannot handle rejection, no pipeline discipline, overpromises
    - Assessment: Role play, pipeline review, campaign analysis
    - Day 60: Learn product deeply, first closed deals, established prospect list

    ## EXPERIENCE TRADE-OFFS

    Generate 4-6 of these UNIVERSAL trade-offs, but frame them for THIS role:
    1. experience_vs_potential: Veteran vs Rising Star
    2. specialist_vs_generalist: Deep expertise vs Broad knowledge
    3. culture_vs_skill: Culture fit vs Functional excellence
    4. stability_vs_growth: Steady contributor vs Fast riser
    5. pedigree_vs_scrappy: Big company polish vs Scrappy background
    6. availability_vs_quality: Available now vs Worth waiting for

    For each, set relevance (high/medium/low/not_relevant) based on THIS role.
    Frame descriptions for the role family - a "specialist" designer is different from a "specialist" engineer.

    ## ROLE-SPECIFIC TRADE-OFFS

    Generate 2 trade-offs UNIQUE to this role's domain. Examples:
    - Designer: "Pixel-perfect craft vs Ship fast"
    - Product: "Data-driven vs Intuition-led"
    - Engineer: "Clean architecture vs Quick wins"
    - Hardware: "Innovation vs Proven reliability"
    - Sales: "Hunting new vs Farming existing"

    ## CAREER TRAJECTORY OPTIONS (trajectoryOptions)

    Generate 4 career growth paths specific to THIS role. Order from entry-level to senior progression (first option = closest next step, last option = most senior path). Hints should explain what that path means.

    AVOID: Abbreviations (write "Individual Contributor" not "IC"), generic options that apply to any job, or titles that just repeat the JD.

    ## WORK STYLE OPTIONS (communicationOptions)

    Generate 4 work/collaboration styles describing HOW they'll work day-to-day. Use styles like "Independent", "Balanced", "Collaborative", "Cross-Functional", "Client-Facing", "Field-Based" as appropriate for the role.

    AVOID: Generic labels like "Team Collaboration" or task descriptions like "Stakeholder Updates".

    {{ ctx.output_format }}
    {{ _.role("user") }}
    Title: {{ job.title }}
    Type: {{ job.positionType }}
    Location: {{ job.locationType }}
    Experience: {{ job.experienceMin }}-{{ job.experienceMax }} years
    Department: {{ job.department }}

    Job Description:
    {{ job.description }}
  "#
}
