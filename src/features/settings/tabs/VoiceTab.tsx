import type React from 'react';

export interface VoiceTabProps {
  selectedVoiceName: string;
  setSelectedVoiceName: (voiceName: string) => void;
  availableVoices: SpeechSynthesisVoice[];
  isPlayingSample: boolean;
  onPlaySample: () => void;
}

export const VoiceTab: React.FC<VoiceTabProps> = ({
  selectedVoiceName,
  setSelectedVoiceName,
  availableVoices,
  isPlayingSample,
  onPlaySample,
}) => {
  return (
    <div className="space-y-6 animate-in fade-in duration-200" data-testid="settings-voice-tab">
      <div>
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">Read Aloud Voice</h3>
        <p className="text-xs text-slate-500 dark:text-[#a8a8a8] mt-1">
          Configure the speech synthesis voice used when reading assistant responses aloud.
        </p>
      </div>

      {/* Voice Selector */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-800 dark:text-slate-200 block">
          Speech Voice
        </label>
        <select
          value={selectedVoiceName}
          onChange={(e) => {
            const val = e.target.value;
            setSelectedVoiceName(val);
            try {
              localStorage.setItem('raise_tts_voice', val);
            } catch {}
          }}
          className="w-full text-xs bg-slate-50 dark:bg-[#12141d] text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-[#37393b] rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 cursor-pointer shadow-xs"
        >
          {availableVoices.length > 0 ? (
            availableVoices.map((v) => (
              <option key={v.name} value={v.name}>
                {v.name} ({v.lang})
              </option>
            ))
          ) : (
            <option value="">Samantha / System Natural Voice</option>
          )}
        </select>
      </div>

      {/* Preview Sample Test Card */}
      <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#282a2c] border border-slate-200/80 dark:border-[#37393b] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg
              className="w-4 h-4 text-indigo-600 dark:text-[#a8c7fa]"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M11 5L6 9H2v6h4l5 4V5z"
              />
            </svg>
            <span className="text-xs font-semibold text-slate-900 dark:text-white">
              Sample Preview
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">Web Speech API</span>
        </div>
        <p className="text-[11px] text-slate-600 dark:text-[#a8a8a8] italic bg-white dark:bg-[#1e1f20] p-2.5 rounded-xl border border-slate-200/60 dark:border-white/5">
          &ldquo;Raise platform connects hybrid dense and sparse embeddings with real-time GraphRAG
          knowledge reasoning.&rdquo;
        </p>
        <button
          type="button"
          onClick={onPlaySample}
          className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-xs"
        >
          {isPlayingSample ? (
            <>
              <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Speaking Sample...</span>
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
              <span>Play Voice Sample</span>
            </>
          )}
        </button>
      </div>

      {/* Info notice */}
      <div className="text-[11px] text-slate-500 dark:text-[#a8a8a8] flex items-start gap-2">
        <svg
          className="w-4 h-4 shrink-0 text-slate-400 mt-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <circle cx="12" cy="12" r="10" strokeWidth="1.75" />
          <line x1="12" y1="16" x2="12" y2="12" strokeWidth="1.75" />
          <line x1="12" y1="8" x2="12.01" y2="8" strokeWidth="2" />
        </svg>
        <span>
          Natural voices provided by your operating system or browser (e.g., Apple Samantha/Siri on
          macOS, Microsoft Natural on Windows, or Google US English) are automatically selected for
          optimal fidelity.
        </span>
      </div>
    </div>
  );
};
