// OpenRouter + shared retry policy for CYOA generation.
// Docs: https://docs.boundaryml.com/ref/llm-client-providers/openrouter

retry_policy GenRetry {
  max_retries 2
  strategy {
    type exponential_backoff
    delay_ms 400
    multiplier 1.5
    max_delay_ms 8000
  }
}

// Primary generation client — uses OPENROUTER_API_KEY from the environment.
// Model defaults to gpt-5.6-terra; override via ClientRegistry in Python if needed.
client<llm> OpenRouter {
  provider openrouter
  retry_policy GenRetry
  options {
    model "openai/gpt-5.6-terra"
    api_key env.OPENROUTER_API_KEY
    temperature 1.15
    headers {
      "HTTP-Referer" "http://127.0.0.1:8765"
      "X-Title" "ai-cyoa"
    }
  }
}

// Fallback if the native openrouter provider is unavailable in older runtimes.
client<llm> OpenRouterGeneric {
  provider openai-generic
  retry_policy GenRetry
  options {
    base_url "https://openrouter.ai/api/v1"
    api_key env.OPENROUTER_API_KEY
    model "openai/gpt-5.6-terra"
    temperature 1.15
    headers {
      "HTTP-Referer" "http://127.0.0.1:8765"
      "X-Title" "ai-cyoa"
    }
  }
}
