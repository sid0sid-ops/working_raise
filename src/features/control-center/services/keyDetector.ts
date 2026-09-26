export type DetectedProvider =
  | 'groq'
  | 'gemini'
  | 'nvidia'
  | 'mistral'
  | 'cohere'
  | 'anthropic'
  | 'openai'
  | 'deepseek'
  | 'openrouter'
  | 'custom'
  | 'unknown';

export interface ProviderDetectionResult {
  provider: DetectedProvider;
  displayName: string;
  defaultModel: string;
}

export function detectProviderFromKey(key: string): ProviderDetectionResult {
  const trimmed = key.trim();
  if (!trimmed) {
    return {
      provider: 'unknown',
      displayName: 'Empty Key',
      defaultModel: '',
    };
  }

  // Groq keys start with 'gsk_'
  if (trimmed.startsWith('gsk_')) {
    return {
      provider: 'groq',
      displayName: 'Groq LPU',
      defaultModel: 'llama-3.3-70b-versatile',
    };
  }

  // Google Gemini keys typically start with 'AIzaSy'
  if (trimmed.startsWith('AIzaSy') || trimmed.startsWith('AIza')) {
    return {
      provider: 'gemini',
      displayName: 'Google Gemini',
      defaultModel: 'gemini-2.0-flash',
    };
  }

  // NVIDIA NIM keys start with 'nvapi-'
  if (trimmed.startsWith('nvapi-')) {
    return {
      provider: 'nvidia',
      displayName: 'NVIDIA NIM',
      defaultModel: 'meta/llama-3.2-11b-vision-instruct',
    };
  }

  // Anthropic keys start with 'sk-ant-'
  if (trimmed.startsWith('sk-ant-')) {
    return {
      provider: 'anthropic',
      displayName: 'Anthropic Claude',
      defaultModel: 'claude-3-5-sonnet',
    };
  }

  // Cohere keys
  if (trimmed.startsWith('co-') || trimmed.length === 40) {
    return {
      provider: 'cohere',
      displayName: 'Cohere Command',
      defaultModel: 'command-r-plus-08-2024',
    };
  }

  // OpenAI / OpenRouter / DeepSeek
  if (trimmed.startsWith('sk-or-')) {
    return {
      provider: 'openrouter',
      displayName: 'OpenRouter',
      defaultModel: 'anthropic/claude-3-haiku',
    };
  }

  if (trimmed.startsWith('sk-')) {
    // Could be OpenAI or DeepSeek or generic
    return {
      provider: 'openai',
      displayName: 'OpenAI / DeepSeek',
      defaultModel: 'gpt-4o-mini',
    };
  }

  // Mistral keys are 32 chars alphanumeric hex
  if (/^[a-zA-Z0-9]{32}$/.test(trimmed)) {
    return {
      provider: 'mistral',
      displayName: 'Mistral AI',
      defaultModel: 'open-mistral-nemo',
    };
  }

  return {
    provider: 'custom',
    displayName: 'Custom / Universal API',
    defaultModel: 'default',
  };
}
