import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { RaisePage, computeVoiceWaveScale } from '../features/raise/RaisePage';

describe('Voice Query Audio Waveform & X Stop Button', () => {
  let mockRecognitionInstance: any;

  beforeEach(() => {
    localStorage.clear();
    mockRecognitionInstance = {
      continuous: false,
      interimResults: false,
      lang: '',
      start: vi.fn(function (this: any) {
        if (this.onstart) {
          this.onstart();
        }
      }),
      stop: vi.fn(function (this: any) {
        if (this.onend) {
          this.onend();
        }
      }),
      onstart: null,
      onresult: null,
      onerror: null,
      onend: null,
      onspeechstart: null,
      onspeechend: null,
      onsoundstart: null,
      onsoundend: null,
      onaudiostart: null,
    };

    (window as any).SpeechRecognition = vi.fn(() => mockRecognitionInstance);
  });

  afterEach(() => {
    delete (window as any).SpeechRecognition;
    delete (window as any).webkitSpeechRecognition;
  });

  describe('computeVoiceWaveScale', () => {
    it('returns subtle baseline scale (dots ........) when quiet / ambient', () => {
      const scale0 = computeVoiceWaveScale(0.2, false, 0);
      const scale1 = computeVoiceWaveScale(0.8, false, 1);
      expect(scale0).toBeLessThanOrEqual(0.35);
      expect(scale1).toBeLessThanOrEqual(0.35);
    });

    it('returns expanded dynamic scale (stretched lines) when speech is detected', () => {
      const scaleSpeaking0 = computeVoiceWaveScale(0.3, true, 0);
      const scaleSpeaking1 = computeVoiceWaveScale(0.3, true, 1);
      expect(scaleSpeaking0).toBeGreaterThanOrEqual(0.75);
      expect(scaleSpeaking1).toBeGreaterThanOrEqual(0.75);
    });
  });

  describe('Voice Query UI & Interaction Lifecycle', () => {
    it('shows microphone start button initially and hides waveform container', () => {
      render(<RaisePage />);
      expect(screen.getByTestId('voice-query-start-button')).toBeInTheDocument();
      expect(screen.queryByTestId('voice-query-waveform-container')).not.toBeInTheDocument();
      expect(screen.queryByTestId('voice-query-stop-button')).not.toBeInTheDocument();
    });

    it('displays animated waveform lines .......(line) and X stop button when voice query is clicked', () => {
      render(<RaisePage />);

      const startMicBtn = screen.getByTestId('voice-query-start-button');
      fireEvent.click(startMicBtn);

      // Waveform container should be visible
      const waveformContainer = screen.getByTestId('voice-query-waveform-container');
      expect(waveformContainer).toBeInTheDocument();

      // Waveform lines container should be present
      const linesContainer = screen.getByTestId('voice-waveform-lines');
      expect(linesContainer).toBeInTheDocument();

      // 7 sound wave bars should be rendered
      for (let i = 0; i < 7; i++) {
        expect(screen.getByTestId(`voice-wave-bar-${i}`)).toBeInTheDocument();
      }

      // X stop button should be present
      const stopBtn = screen.getByTestId('voice-query-stop-button');
      expect(stopBtn).toBeInTheDocument();
      expect(stopBtn).toHaveAttribute('aria-label', 'Stop Voice Query');
    });

    it('expands dots into taller moving lines when speech is detected', () => {
      render(<RaisePage />);

      const startMicBtn = screen.getByTestId('voice-query-start-button');
      fireEvent.click(startMicBtn);

      // Initially silent: bar heights are 5px (compact dots)
      const bar0Before = screen.getByTestId('voice-wave-bar-0');
      expect(bar0Before.style.height).toBe('5px');

      // User says something (speech event triggers)
      act(() => {
        if (mockRecognitionInstance.onspeechstart) {
          mockRecognitionInstance.onspeechstart();
        }
      });

      // After speech detected: bar expands to 18px line
      const bar0After = screen.getByTestId('voice-wave-bar-0');
      expect(bar0After.style.height).toBe('18px');
    });

    it('clicking X button immediately stops the voice query and restores microphone button', () => {
      render(<RaisePage />);

      const startMicBtn = screen.getByTestId('voice-query-start-button');
      fireEvent.click(startMicBtn);

      // Verify active
      expect(screen.getByTestId('voice-query-waveform-container')).toBeInTheDocument();

      // Click X stop button
      const stopBtn = screen.getByTestId('voice-query-stop-button');
      fireEvent.click(stopBtn);

      // Waveform and X stop button should disappear
      expect(screen.queryByTestId('voice-query-waveform-container')).not.toBeInTheDocument();
      expect(screen.queryByTestId('voice-query-stop-button')).not.toBeInTheDocument();

      // Standard microphone button should be restored
      expect(screen.getByTestId('voice-query-start-button')).toBeInTheDocument();
      expect(mockRecognitionInstance.stop).toHaveBeenCalled();
    });

    it('displays live timer and floating listening indicator when microphone starts', () => {
      render(<RaisePage />);

      const startMicBtn = screen.getByTestId('voice-query-start-button');
      fireEvent.click(startMicBtn);

      // Verify timer is displayed
      expect(screen.getByText('0:00')).toBeInTheDocument();

      // Verify listening badge / placeholder
      expect(screen.getByText(/Listening... Speak your research inquiry/i)).toBeInTheDocument();
    });

    it('renders quick submit checkmark button when spoken transcript is produced', () => {
      render(<RaisePage />);

      const startMicBtn = screen.getByTestId('voice-query-start-button');
      fireEvent.click(startMicBtn);

      // Initially empty: submit button is not rendered
      expect(screen.queryByTestId('voice-query-submit-button')).not.toBeInTheDocument();

      // Speech recognition produces result
      act(() => {
        if (mockRecognitionInstance.onresult) {
          mockRecognitionInstance.onresult({
            results: [[{ transcript: 'What is the patent count?' }]],
          });
        }
      });

      // Quick submit button should now be rendered
      expect(screen.getByTestId('voice-query-submit-button')).toBeInTheDocument();
      expect(screen.getByTestId('voice-query-submit-button')).toHaveAttribute('aria-label', 'Send Spoken Inquiry');
    });
  });
});
