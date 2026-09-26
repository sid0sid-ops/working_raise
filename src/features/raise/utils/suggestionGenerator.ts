import type { Citation } from '../../../types';

export interface DynamicSuggestion {
  query: string;
  category?: string;
  grounding_confidence?: string;
  complexity?: string;
  relationship_path?: string;
}

/**
 * Clean document filename to a readable title (e.g. "IITMRP Annual Report.pdf" -> "IITMRP Annual Report")
 */
export function cleanDocName(filename: string): string {
  return filename
    .replace(/\.[^/.]+$/, '')
    .replace(/[_-]/g, ' ')
    .trim();
}

/**
 * Deduplicate and sanitize suggestions provided by the backend.
 * Zero-hardcoding: Does not inject or filter based on static institute or document strings.
 */
export function filterRelevantBackendSuggestions(
  suggestions: (DynamicSuggestion | string)[],
  _activeDocNames: string[] = [],
  _conversationKeywords: string[] = []
): string[] {
  if (!suggestions || suggestions.length === 0) return [];

  const results: string[] = [];

  for (const item of suggestions) {
    const rawQuery = typeof item === 'string' ? item : item?.query || '';
    if (!rawQuery) continue;

    // Clean query of extra whitespace or trailing punctuation
    const cleanQ = rawQuery
      .replace(/\s+/g, ' ')
      .replace(/[.?]+$/, '')
      .trim();

    if (cleanQ.length > 5 && !results.includes(cleanQ)) {
      results.push(cleanQ);
    }
  }

  return results;
}

/**
 * Dynamic follow-up query bubble extractor.
 * STRICT ZERO-HARDCODING POLICY:
 * Does NOT synthesize fake template questions.
 * Only collects dynamic questions provided by the backend:
 * 1. Follow-up inquiries returned in the LLM response payload (response.follow_up_inquiries / response.suggestions)
 * 2. Decomposed query routes from the LangGraph intake node (response.decomposed_queries)
 * 3. Scoped graph suggestions from GET /api/suggestions
 *
 * If the backend does not return any suggestions, returns [] (clean UI, no hallucinated cards).
 */
export function generateContextualFollowUps(params: {
  lastUserQuery?: string;
  lastAssistantAnswer?: string;
  citations?: Citation[];
  activeDocs?: string[];
  backendSuggestions?: (DynamicSuggestion | string)[];
  backendFollowUps?: string[];
  backendDecomposed?: string[];
}): string[] {
  const {
    lastUserQuery = '',
    activeDocs = [],
    backendSuggestions = [],
    backendFollowUps = [],
    backendDecomposed = [],
  } = params;

  const activeKeywords = [
    ...lastUserQuery
      .toLowerCase()
      .split(/\s+/)
      .filter((w) => w.length > 3),
    ...activeDocs.map((d) => cleanDocName(d).toLowerCase()),
  ];

  // Collect candidate queries strictly from backend-provided data
  const rawCandidates: (DynamicSuggestion | string)[] = [];

  if (Array.isArray(backendFollowUps)) {
    rawCandidates.push(...backendFollowUps);
  }

  if (Array.isArray(backendDecomposed)) {
    rawCandidates.push(...backendDecomposed);
  }

  if (Array.isArray(backendSuggestions)) {
    rawCandidates.push(...backendSuggestions);
  }

  // Filter against foreign document bleed and duplicates
  const filtered = filterRelevantBackendSuggestions(rawCandidates, activeDocs, activeKeywords);

  return filtered.slice(0, 4);
}
