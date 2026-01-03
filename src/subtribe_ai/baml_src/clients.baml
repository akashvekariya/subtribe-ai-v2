// LLM Client Definitions for Subtribe AI
// Consolidated from subtribe-poc and resume-screener

// ============================================================================
// GOOGLE GEMINI CLIENTS
// ============================================================================

// Gemini 2.0 Flash - Fast, general purpose
client<llm> Gemini2_0Flash {
  provider google-ai
  options {
    model "gemini-2.0-flash"
    api_key env.SUBTRIBE_AI_GOOGLE_API_KEY
    generationConfig {
      thinkingConfig {
        thinkingBudget 0
      }
      temperature 0
      topP 0.7
      topK 10
      maxOutputTokens 5000
    }
  }
}

// Gemini 2.0 Flash Lite - Lightweight tasks
client<llm> Gemini2_0FlashLite {
  provider google-ai
  options {
    model "gemini-2.0-flash-lite"
    api_key env.SUBTRIBE_AI_GOOGLE_API_KEY
    generationConfig {
      thinkingConfig {
        thinkingBudget 0
      }
      temperature 0
      topP 0.7
      topK 10
      maxOutputTokens 5000
    }
  }
}

// Gemini 2.5 Flash - Latest fast model
client<llm> Gemini2_5Flash {
  provider google-ai
  options {
    model "gemini-2.5-flash"
    api_key env.SUBTRIBE_AI_GOOGLE_API_KEY
    generationConfig {
      thinkingConfig {
        thinkingBudget 0
      }
      temperature 0
      topP 0.7
      topK 10
      maxOutputTokens 5000
    }
  }
}

// Gemini 2.5 Flash Lite - Lightweight, no thinking
client<llm> Gemini2_5FlashLite {
  provider "google-ai"
  options {
    api_key env.SUBTRIBE_AI_GOOGLE_API_KEY
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

// Gemini 3 Flash Preview - With thinking budget
client<llm> Gemini3FlashPreview {
  provider "google-ai"
  options {
    api_key env.SUBTRIBE_AI_GOOGLE_API_KEY
    model "gemini-3-flash-preview"
    generationConfig: {
      thinkingConfig: {
        thinkingBudget: 2000
      }
      temperature 0
      topP 0.1
      topK 1
    }
  }
}

// Gemini 3 Flash Preview - For Candidate Evaluations (higher temperature)
client<llm> Gemini3FlashPreview_CandidateEvals {
  provider "google-ai"
  options {
    api_key env.SUBTRIBE_AI_GOOGLE_API_KEY
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

// Gemini 3 Pro Preview - Most capable
client<llm> Gemini3Pro {
  provider "google-ai"
  options {
    api_key env.SUBTRIBE_AI_GOOGLE_API_KEY
    model "gemini-3-pro-preview"
    generationConfig: {
      thinkingConfig: {
        thinkingBudget: 1000
      }
      temperature 0.2
      topP 0.5
      topK 5
    }
  }
}

// ============================================================================
// OPENAI CLIENTS
// ============================================================================

// OpenAI GPT-5 Nano - Fast, lightweight
client<llm> OpenAI5Nano {
  provider openai-responses
  options {
    model "gpt-5-nano"
    api_key env.SUBTRIBE_AI_OPENAI_API_KEY
    reasoning {
      effort "minimal"
    }
  }
}

// ============================================================================
// OPENROUTER CLIENTS (Fallback/Alternative)
// ============================================================================

// OpenRouter Gemini 2.5 Flash Lite
client<llm> OpenRouter_Gemini2_5FlashLite_High {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    api_key env.SUBTRIBE_AI_OPENROUTER_API_KEY
    model "google/gemini-2.5-flash-lite"
    headers {
      "X-Title" "Subtribe"
    }
    reasoning {
      exclude true
    }
    temperature 0.3
    top_p 0.5
    top_k 5
    max_tokens 5000
  }
}
