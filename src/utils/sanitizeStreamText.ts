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

  return cleaned;
}
