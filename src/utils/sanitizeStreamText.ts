/**
 * Sanitizes stream output by stripping SSE artifacts and unpacking any leaked JSON token fragments.
 * Handles cases where network chunk boundary anomalies or legacy strings contain raw JSON blocks:
 *   Hello! Ask me any{"token": " question "} {"token": "regarding"} research
 *   -> Hello! Ask me any question regarding research
 */
export function sanitizeStreamText(text: string): string {
  if (!text) return '';
  let cleaned = text;

  // 1. Unpack nested delta content if present: {"delta": {"content": "..."}}
  cleaned = cleaned.replace(/\{"delta":\s*\{"content":\s*"((?:[^"\\]|\\.)*)"\}\}/g, (_, inner) => {
    try {
      return JSON.parse(`"${inner}"`);
    } catch {
      return inner;
    }
  });

  // 2. Unpack standard JSON tokens: {"token": "..."} / {"text": "..."} / {"content": "..."}
  cleaned = cleaned.replace(
    /\{"(?:token|text|content|response|reply)":\s*"((?:[^"\\]|\\.)*)"\}/g,
    (_, inner) => {
      try {
        return JSON.parse(`"${inner}"`);
      } catch {
        return inner;
      }
    }
  );

  // 3. Strip stray SSE line artifacts if any leaked into final text
  cleaned = cleaned
    .replace(/^data:\s*/gm, '')
    .replace(/^:\s*keepalive\s*$/gm, '')
    .replace(/\[DONE\]/g, '');

  // 4. Strip non-printable control characters (except \t, \n, \r) like \x08 backspaces
  cleaned = cleaned.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

  // 5. Strip literal escaped control character sequences from PDF/OCR extractors (e.g. \x08, \u0008)
  cleaned = cleaned.replace(/\\x0[0-8bBcCeEfF]|\\x1[0-9a-fA-F]|\\x7[fF]|\\u000[0-8bBcCeEfF]|\\u001[0-9a-fA-F]/g, '');

  // 6. Ensure double newlines before bullets so glued list items (e.g. "...text• **Title**") are properly spaced
  cleaned = cleaned.replace(/([^\n])\s*•\s*/g, '$1\n\n• ');

  // 7. Normalize excess blank lines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  return cleaned;
}
