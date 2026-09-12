import React from 'react';
import { computeVoiceWaveScale } from '../../features/raise/utils/speechUtils';

export interface VoiceInputButtonProps {
  isListening: boolean;
  isVoiceSpeaking: boolean;
  voiceAudioLevels: number[];
  voiceDurationSec: number;
  hasSpeechContent: boolean;
  onToggleVoice: () => void;
  onSubmitVoice: () => void;
  formatVoiceDuration?: (sec: number) => string;
}

export const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  isListening,
  isVoiceSpeaking,
  voiceAudioLevels,
  voiceDurationSec,
  hasSpeechContent,
  onToggleVoice,
  onSubmitVoice,
  formatVoiceDuration = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  },
}) => {
  if (!isListening) {
    return (
      <button
        type="button"
        onClick={onToggleVoice}
        title="Voice query"
        aria-label="Voice Query"
        data-testid="voice-query-start-button"
        className="p-1 sm:p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-white/5 transition-all cursor-pointer"
      >
        <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
          />
        </svg>
      </button>
    );
  }

  return (
    <div
      data-testid="voice-query-waveform-container"
      className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full bg-rose-50/90 dark:bg-rose-950/40 border border-rose-200/80 dark:border-rose-500/30 shadow-xs backdrop-blur-xs transition-all select-none animate-in fade-in zoom-in-95 duration-150"
      title={isVoiceSpeaking ? 'Speaking detected' : 'Listening...'}
    >
      {/* Pulsing indicator dot & live duration timer */}
      <span className="flex items-center gap-1.5 shrink-0">
        <span className="relative flex h-2 w-2">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75 ${
              isVoiceSpeaking ? 'duration-300' : 'duration-1000'
            }`}
          />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
        </span>
        <span className="text-[11px] font-mono font-semibold text-rose-600 dark:text-rose-400 select-none">
          {formatVoiceDuration(voiceDurationSec)}
        </span>
      </span>

      {/* Moving lines: .......(line) that move as user speaks */}
      <div
        data-testid="voice-waveform-lines"
        className="flex items-center gap-0.5 sm:gap-1 h-5 px-0.5 select-none"
        role="img"
        aria-label="Audio waveform"
      >
        {voiceAudioLevels.map((level, idx) => {
          const activeScale = computeVoiceWaveScale(level, isVoiceSpeaking, idx);
          return (
            <span
              key={idx}
              data-testid={`voice-wave-bar-${idx}`}
              className={`w-0.75 sm:w-1 rounded-full transition-all duration-100 ${
                isVoiceSpeaking
                  ? 'bg-gradient-to-t from-rose-500 via-indigo-500 to-indigo-400 dark:from-rose-400 dark:via-indigo-400 dark:to-indigo-300'
                  : 'bg-rose-400/70 dark:bg-rose-400/50'
              }`}
              style={{
                height: isVoiceSpeaking ? '18px' : '5px',
                transform: `scaleY(${activeScale})`,
                transformOrigin: 'center',
                animation: isVoiceSpeaking
                  ? `voiceWaveBar 0.55s ease-in-out infinite alternate ${idx * 0.08}s`
                  : `voiceWaveIdle 1.3s ease-in-out infinite alternate ${idx * 0.15}s`,
              }}
            />
          );
        })}
      </div>

      {/* Quick submit button (✓) if voice produced text */}
      {hasSpeechContent && (
        <button
          type="button"
          onClick={onSubmitVoice}
          title="Send spoken inquiry"
          aria-label="Send Spoken Inquiry"
          data-testid="voice-query-submit-button"
          className="w-5 h-5 sm:w-5.5 sm:h-5.5 rounded-full flex items-center justify-center text-emerald-600 hover:text-emerald-700 bg-emerald-100/90 hover:bg-emerald-200 dark:text-emerald-300 dark:bg-emerald-500/20 dark:hover:bg-emerald-500/30 active:scale-90 transition-all cursor-pointer"
        >
          <svg className="w-3 h-3 sm:w-3.5 sm:h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </button>
      )}

      {/* X button: stops the voice query immediately */}
      <button
        type="button"
        onClick={onToggleVoice}
        title="Stop voice query"
        aria-label="Stop Voice Query"
        data-testid="voice-query-stop-button"
        className="w-5 h-5 sm:w-5.5 sm:h-5.5 rounded-full flex items-center justify-center text-slate-400 hover:text-rose-600 hover:bg-rose-100 dark:text-slate-400 dark:hover:text-rose-400 dark:hover:bg-rose-500/20 active:scale-90 transition-all cursor-pointer"
      >
        <svg
          className="w-3 h-3 sm:w-3.5 sm:h-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
};
