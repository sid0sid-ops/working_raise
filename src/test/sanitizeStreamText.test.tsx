import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { sanitizeStreamText } from '../utils/sanitizeStreamText';
import { AnswerMarkdown } from '../components/chat/AnswerMarkdown';

describe('sanitizeStreamText', () => {
  it('unpacks raw {"token": "..."} JSON fragments into plain string', () => {
    const raw = 'Hello! I am the RAISE Academi{"token": " question "} {"token": "regarding university"} research {"token": "parks, financial"} metrics, incubation numbers, or {"token": "faculty patents."}';
    const cleaned = sanitizeStreamText(raw);
    expect(cleaned).toBe(
      'Hello! I am the RAISE Academi question  regarding university research parks, financial metrics, incubation numbers, or faculty patents.'
    );
    expect(cleaned).not.toContain('{"token"');
  });

  it('unpacks text, content, and nested delta fields', () => {
    const input = 'Prefix {"text": "middle"} and {"content": "end"} with {"delta": {"content": "!"}}';
    expect(sanitizeStreamText(input)).toBe('Prefix middle and end with !');
  });

  it('strips stray SSE artifacts (data: and [DONE])', () => {
    const sse = 'data: Hello world\ndata: [DONE]';
    expect(sanitizeStreamText(sse).trim()).toBe('Hello world');
  });

  it('returns empty string for null or empty input', () => {
    expect(sanitizeStreamText('')).toBe('');
    expect(sanitizeStreamText(null as any)).toBe('');
  });
});

describe('AnswerMarkdown token sanitization', () => {
  it('renders clean readable answer even if raw token JSON fragments are passed', () => {
    const rawAnswer = 'Hello! I am RAISE. Ask me any{"token": " question "} {"token": "regarding university"} research.';
    render(<AnswerMarkdown content={rawAnswer} />);

    expect(screen.queryByText(/\{"token":/i)).toBeNull();
    expect(screen.getByText(/Ask me any question regarding university research\./i)).toBeDefined();
  });
});
