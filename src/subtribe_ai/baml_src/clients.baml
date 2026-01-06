// ============================================================================
// PURPOSE-SPECIFIC CLIENTS
// ============================================================================

// Resume PDF to Markdown extraction
client<llm> Gemini2_5FlashLite__CandidateResumeToMarkdown {
  provider "google-ai"
  options {
    api_key env.GOOGLE_API_KEY
    model "gemini-2.5-flash-lite"
    generationConfig: {
      thinkingConfig: {
        thinkingBudget: 0
      }
      temperature 0
      topP 0.1
      topK 1
    }
  }
}

// Markdown to structured JSON parsing
client<llm> Gemini2_5FlashLite__CandidateResumeMarkdownToJson {
  provider "google-ai"
  options {
    api_key env.GOOGLE_API_KEY
    model "gemini-2.5-flash-lite"
    generationConfig: {
      thinkingConfig: {
        thinkingBudget: 0
      }
      temperature 0
      topP 0.1
      topK 1
    }
  }
}

// Job description to Calibration generation
client<llm> Gemini3FlashPreview__JobToCalibration {
  provider "google-ai"
  options {
    api_key env.GOOGLE_API_KEY
    model "gemini-3-flash-preview"
    generationConfig: {
      thinkingConfig: {
        thinkingBudget: 2000
      }
      temperature 0.7
      topP 1
      topK 10
    }
  }
}

// Calibration to Evaluation Framework generation
client<llm> Gemini3FlashPreview__JobCalibrationToFramework {
  provider "google-ai"
  options {
    api_key env.GOOGLE_API_KEY
    model "gemini-3-flash-preview"
    generationConfig: {
      thinkingConfig: {
        thinkingBudget: 2000
      }
      temperature 0.7
      topP 1
      topK 10
    }
  }
}

// Candidate evaluation using Framework + Resume JSON
client<llm> Gemini2_5FlashLite__CandidateEvaluation {
  provider "google-ai"
  options {
    api_key env.GOOGLE_API_KEY
    model "gemini-2.5-flash-lite"
    generationConfig: {
      thinkingConfig: {
        thinkingBudget: 0
      }
      temperature 0
      topP 0.1
      topK 1
    }
  }
}