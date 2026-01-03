// Fact Extraction Types
// Types for Phase 1: Extract structured facts from resume
// LLM outputs these, Python post-processing enriches them

// ============================================================================
// ENUMS
// ============================================================================

enum RawExperienceType {
  FullTime @alias("full_time") @description("Regular full-time employment (default if not specified)")
  Internship @alias("internship") @description("Internship or co-op position")
  Freelance @alias("freelance") @description("Freelance or consulting work")
  Contract @alias("contract") @description("Fixed-term contract position")
  PartTime @alias("part_time") @description("Part-time employment")
  StartupFounder @alias("startup_founder") @description("Founded or co-founded a startup")
  AcademicProject @alias("academic_project") @description("Significant academic/university project")
  PersonalProject @alias("personal_project") @description("Personal or open-source project")
}

// ============================================================================
// DATE EXTRACTION - Separate month and year to avoid format ambiguity
// ============================================================================

class ExtractedDate {
  year int @description("4-digit year, e.g., 2022")
  month int @description("Month as number 1-12. If only year given, use 6 (mid-year). If vague like 'Summer', use: Spring=3, Summer=6, Fall=9, Winter=12, Q1=2, Q2=5, Q3=8, Q4=11")
  is_estimated bool @description("True if month was estimated (only year given, or vague like 'Summer 2021')")
}

// ============================================================================
// EXPERIENCE EXTRACTION
// ============================================================================

class RawExperienceEntry {
  company string @description("Company or organization name exactly as stated in resume")
  title string @description("Job title or role exactly as stated")
  location string? @description("Location if mentioned (city, state, country)")
  experience_type RawExperienceType @description("Type of experience. Use full_time as default if not explicitly stated as internship/freelance/etc.")

  start_date ExtractedDate? @description("Start date. Extract year and month. Null ONLY if no start date mentioned at all.")
  end_date ExtractedDate? @description("End date. Extract year and month. Null ONLY if resume says 'Present', 'Current', 'Now', or indicates ongoing role.")
  is_ongoing bool @description("True if this is a current/ongoing role (resume says Present, Current, Now, or no end date with context suggesting ongoing)")

  duration_stated string? @description("If resume explicitly states duration like '2.5 years' or '8 months', capture the exact text here. Otherwise null.")

  key_contributions string[] @description("2-4 key achievements or contributions in this role")
  skills_demonstrated string[] @description("skill_ids from framework that are evidenced in this experience")
}

// ============================================================================
// EDUCATION EXTRACTION
// ============================================================================

class RawEducationEntry {
  institution string @description("University, college, or school name")
  degree string @description("Degree type: B.Tech, M.Tech, MBA, PhD, etc.")
  field_of_study string? @description("Major or specialization if stated")
  graduation_year int? @description("Year of graduation or expected graduation")
  graduation_month int? @description("Month of graduation if stated (1-12)")
  grade string? @description("GPA, CGPA, percentage, or other grade as stated")
  is_current bool @description("True if currently pursuing this degree")
}

// ============================================================================
// CERTIFICATION EXTRACTION
// ============================================================================

class RawCertificationEntry {
  name string @description("Certification name exactly as stated")
  issuer string? @description("Issuing organization (AWS, Google, etc.)")
  year int? @description("Year obtained")
  month int? @description("Month obtained if stated (1-12)")
}

// ============================================================================
// COMPLETE EXTRACTION OUTPUT
// ============================================================================

class ExtractedResumeFacts {
  experience_entries RawExperienceEntry[] @description("All work experience, internships, and significant projects. Extract EACH separately. Include ALL entries even if dates are missing.")
  education_entries RawEducationEntry[] @description("All education entries")
  certifications RawCertificationEntry[] @description("All certifications mentioned")
  skill_keywords string[] @description("Raw skill keywords found in resume (from skills section and throughout). Include technologies, tools, frameworks, languages.")
}
