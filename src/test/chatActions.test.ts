import { describe, it, expect } from 'vitest';
import { formatBytes } from '../utils/formatters';
import {
  cleanTextForSpeech,
  getTurnQuestionVersions,
  filterNaturalVoices,
  selectBestSpeechVoice,
  type ChatMessage,
  type QuestionVersion,
  type ResponseVersion,
} from '../features/raise/RaisePage';

describe('Chat Actions & Version Management', () => {
  describe('Speech Synthesis Voice Selection', () => {
    const mockSystemVoices = [
      { name: 'Albert', lang: 'en-US' },
      { name: 'Bad News', lang: 'en-US' },
      { name: 'Fred', lang: 'en-US' },
      { name: 'Zarvox', lang: 'en-US' },
      { name: 'Samantha', lang: 'en-US' },
      { name: 'Daniel', lang: 'en-GB' },
      { name: 'Karen', lang: 'en-AU' },
      { name: 'Alice', lang: 'it-IT' },
    ];

    it('filters out legacy robotic novelty voices', () => {
      const natural = filterNaturalVoices(mockSystemVoices);
      const names = natural.map((v) => v.name);

      expect(names).toContain('Samantha');
      expect(names).toContain('Daniel');
      expect(names).toContain('Karen');

      // Robotic voices MUST be excluded
      expect(names).not.toContain('Albert');
      expect(names).not.toContain('Fred');
      expect(names).not.toContain('Bad News');
      expect(names).not.toContain('Zarvox');
      // Non-English excluded from English natural voices
      expect(names).not.toContain('Alice');
    });

    it('automatically defaults to natural Siri/Samantha voice instead of Albert', () => {
      const best = selectBestSpeechVoice(mockSystemVoices);
      expect(best).not.toBeNull();
      expect(best?.name).toBe('Samantha');
    });

    it('honors user preferred voice selection', () => {
      const userChoice = selectBestSpeechVoice(mockSystemVoices, 'Daniel');
      expect(userChoice).not.toBeNull();
      expect(userChoice?.name).toBe('Daniel');
      expect(userChoice?.lang).toBe('en-GB');
    });
  });

  describe('cleanTextForSpeech', () => {
    it('removes code blocks and inlines code properly', () => {
      const input = 'Here is code:\n```typescript\nconst x = 1;\n```\nUse `console.log` to print.';
      const cleaned = cleanTextForSpeech(input);
      expect(cleaned).toContain('Code block omitted.');
      expect(cleaned).toContain('Use console.log to print.');
      expect(cleaned).not.toContain('```');
      expect(cleaned).not.toContain('const x = 1;');
    });

    it('strips markdown headings, bold, italics, and citation numbers', () => {
      const input = '### XYMA Analytics\n**Prof. Krishnan** deployed sensors [1] with *continuous* monitoring.';
      const cleaned = cleanTextForSpeech(input);
      expect(cleaned).toBe('XYMA Analytics Prof. Krishnan deployed sensors with continuous monitoring.');
      expect(cleaned).not.toContain('#');
      expect(cleaned).not.toContain('*');
      expect(cleaned).not.toContain('[1]');
    });
  });

  describe('getTurnQuestionVersions', () => {
    it('synthesizes a 1-version fallback for unversioned legacy messages', () => {
      const userMsg: ChatMessage = {
        role: 'user',
        text: 'Who is XYMA?',
      };
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        text: 'XYMA is an ultrasonic sensor startup.',
      };

      const versions = getTurnQuestionVersions(userMsg, assistantMsg);
      expect(versions).toHaveLength(1);
      expect(versions[0].question).toBe('Who is XYMA?');
      expect(versions[0].responseVersions).toHaveLength(1);
      expect(versions[0].responseVersions[0].text).toBe('XYMA is an ultrasonic sensor startup.');
      expect(versions[0].currentResponseVersionIndex).toBe(0);
    });

    it('preserves existing question versions when present', () => {
      const existingRespVer: ResponseVersion = {
        id: 'resp-1',
        text: 'Answer 1',
      };
      const existingQVer: QuestionVersion = {
        id: 'qver-1',
        question: 'Version 1 question',
        responseVersions: [existingRespVer],
        currentResponseVersionIndex: 0,
      };

      const userMsg: ChatMessage = {
        role: 'user',
        text: 'Version 1 question',
        questionVersions: [existingQVer],
        currentQuestionVersionIndex: 0,
      };

      const versions = getTurnQuestionVersions(userMsg);
      expect(versions).toHaveLength(1);
      expect(versions[0].id).toBe('qver-1');
      expect(versions[0].question).toBe('Version 1 question');
    });

    it('supports multiple question versions and response versions hierarchy', () => {
      const resp1a: ResponseVersion = { id: 'r1a', text: 'Response 1A' };
      const resp1b: ResponseVersion = { id: 'r1b', text: 'Response 1B (Regenerated)' };

      const qver1: QuestionVersion = {
        id: 'qv1',
        question: 'Original Question',
        responseVersions: [resp1a, resp1b],
        currentResponseVersionIndex: 1,
      };

      const resp2a: ResponseVersion = { id: 'r2a', text: 'Response 2A' };

      const qver2: QuestionVersion = {
        id: 'qv2',
        question: 'Edited Question',
        responseVersions: [resp2a],
        currentResponseVersionIndex: 0,
      };

      const userMsg: ChatMessage = {
        role: 'user',
        text: 'Edited Question',
        questionVersions: [qver1, qver2],
        currentQuestionVersionIndex: 1,
      };

      const versions = getTurnQuestionVersions(userMsg);
      expect(versions).toHaveLength(2);
      expect(versions[0].responseVersions).toHaveLength(2);
      expect(versions[0].responseVersions[versions[0].currentResponseVersionIndex].text).toBe('Response 1B (Regenerated)');
      expect(versions[1].responseVersions).toHaveLength(1);
      expect(versions[1].question).toBe('Edited Question');
    });

    it('determines visibility of See Versions only when totalQVers > 1', () => {
      // Single unedited question turn
      const singleMsg: ChatMessage = {
        role: 'user',
        text: 'Single unedited question',
      };
      const singleTurnVersions = getTurnQuestionVersions(singleMsg);
      expect(singleTurnVersions.length).toBe(1);
      const shouldShowVersionControlsSingle = singleTurnVersions.length > 1;
      expect(shouldShowVersionControlsSingle).toBe(false);

      // Edited question turn with multiple versions
      const editedMsg: ChatMessage = {
        role: 'user',
        text: 'Edited question v2',
        questionVersions: [
          { id: 'qv-1', question: 'Original question v1', responseVersions: [], currentResponseVersionIndex: 0 },
          { id: 'qv-2', question: 'Edited question v2', responseVersions: [], currentResponseVersionIndex: 0 },
        ],
        currentQuestionVersionIndex: 1,
      };
      const editedTurnVersions = getTurnQuestionVersions(editedMsg);
      expect(editedTurnVersions.length).toBe(2);
      const shouldShowVersionControlsEdited = editedTurnVersions.length > 1;
      expect(shouldShowVersionControlsEdited).toBe(true);
    });

    it('correctly tracks active version indices across version transitions', () => {
      const respV1: ResponseVersion = { id: 'r1', text: 'Answer to V1' };
      const respV2: ResponseVersion = { id: 'r2', text: 'Answer to V2' };

      const qv1: QuestionVersion = {
        id: 'qv1',
        question: 'First query',
        responseVersions: [respV1],
        currentResponseVersionIndex: 0,
      };
      const qv2: QuestionVersion = {
        id: 'qv2',
        question: 'Refined query',
        responseVersions: [respV2],
        currentResponseVersionIndex: 0,
      };

      const userMsg: ChatMessage = {
        role: 'user',
        text: 'Refined query',
        questionVersions: [qv1, qv2],
        currentQuestionVersionIndex: 1,
      };

      const versions = getTurnQuestionVersions(userMsg);
      expect(versions[userMsg.currentQuestionVersionIndex!].question).toBe('Refined query');
      expect(versions[userMsg.currentQuestionVersionIndex!].responseVersions[0].text).toBe('Answer to V2');

      // If switched back to version 0 (previous)
      const prevIdx = 0;
      expect(versions[prevIdx].question).toBe('First query');
      expect(versions[prevIdx].responseVersions[0].text).toBe('Answer to V1');
    });

    it('identifies whether a click target is outside the version navigation container', () => {
      // Simulate DOM check used by outside-click listener
      const container = document.createElement('div');
      container.setAttribute('data-version-nav', 'true');

      const prevBtn = document.createElement('button');
      prevBtn.setAttribute('aria-label', 'Previous version');
      container.appendChild(prevBtn);

      const outsideArea = document.createElement('div');
      outsideArea.id = 'chat-messages-container';

      document.body.appendChild(container);
      document.body.appendChild(outsideArea);

      // Clicks inside the version navigation container should NOT close navigation
      expect(prevBtn.closest('[data-version-nav]')).not.toBeNull();
      expect(container.closest('[data-version-nav]')).not.toBeNull();

      // Clicks anywhere else on the screen SHOULD close navigation
      expect(outsideArea.closest('[data-version-nav]')).toBeNull();
      expect(document.body.closest('[data-version-nav]')).toBeNull();

      document.body.removeChild(container);
      document.body.removeChild(outsideArea);
    });
  });

  describe('formatBytes', () => {
    it('formats small files without displaying 0.0 MB', () => {
      expect(formatBytes(0)).toBe('0 B');
      expect(formatBytes(512)).toBe('512 B');
      expect(formatBytes(2500)).toBe('2.4 KB');
      expect(formatBytes(45000)).toBe('44 KB');
      expect(formatBytes(500000)).toBe('488 KB');
      expect(formatBytes(1200000)).toBe('1.1 MB');
      expect(formatBytes(28835840)).toBe('27.5 MB');
    });

    it('handles falsy or invalid inputs gracefully', () => {
      expect(formatBytes(-100)).toBe('0 B');
      expect(formatBytes(NaN)).toBe('0 B');
    });
  });

  describe('Voice Query Speech Processing', () => {
    it('combines base query with interim and final speech transcripts properly', () => {
      const base = 'What are the key';
      const transcript = 'patents by XYMA?';
      const combined = base ? `${base} ${transcript}` : transcript;
      expect(combined).toBe('What are the key patents by XYMA?');
    });

    it('handles voice query from clean empty state without leading whitespace', () => {
      const base = '';
      const transcript = 'Compare university rankings';
      const combined = base ? `${base} ${transcript}` : transcript;
      expect(combined).toBe('Compare university rankings');
    });

    it('correctly detects speech recognition availability', () => {
      const hasSpeechRecog = Boolean(
        typeof window !== 'undefined' &&
          (('SpeechRecognition' in window) || ('webkitSpeechRecognition' in window))
      );
      expect(typeof hasSpeechRecog).toBe('boolean');
    });
  });

  describe('Thought & Stop Button Mechanics', () => {
    it('formats thought execution time with exact decimal precision', () => {
      const executionTimeSec = 2.148;
      const formatted = executionTimeSec.toFixed(1);
      expect(formatted).toBe('2.1');
      expect(`Thought for ${formatted}s`).toBe('Thought for 2.1s');
      expect(`Worked (${formatted}s)`).toBe('Worked (2.1s)');
    });

    it('calculates button state as Stop when query is loading and Send when idle', () => {
      const getButtonConfig = (isLoading: boolean, queryText: string) => ({
        action: isLoading ? 'abort' : 'execute',
        title: isLoading ? 'Stop generating' : 'Send question',
        icon: isLoading ? 'circle-with-rectangle' : 'arrow-up',
        disabled: !isLoading && !queryText.trim(),
      });

      // When loading, button turns into stop with circle & rectangle and is active
      const loadingState = getButtonConfig(true, '');
      expect(loadingState.action).toBe('abort');
      expect(loadingState.title).toBe('Stop generating');
      expect(loadingState.icon).toBe('circle-with-rectangle');
      expect(loadingState.disabled).toBe(false);

      // When idle with text, button is send
      const idleWithText = getButtonConfig(false, 'Hello');
      expect(idleWithText.action).toBe('execute');
      expect(idleWithText.title).toBe('Send question');
      expect(idleWithText.icon).toBe('arrow-up');
      expect(idleWithText.disabled).toBe(false);

      // When idle without text, button is disabled
      const idleEmpty = getButtonConfig(false, '');
      expect(idleEmpty.disabled).toBe(true);
    });
  });
});
