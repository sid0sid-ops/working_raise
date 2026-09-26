import type React from 'react';
import { VoiceInputButton } from '../../../components/input/VoiceInputButton';
import type { DynamicSuggestion, SourceDocument } from '../../../types';
import { AddSourceButton, AttachedDocChips, FastExpertToggle } from '../query-controls';

export interface QueryBoxProps {
  /** Current text query entered by the user */
  query: string;
  /** Callback fired when user types into the textarea */
  onQueryChange: (value: string) => void;
  /** Callback to execute / submit the query */
  onSubmit: () => void;
  /** Callback to abort / stop active generation */
  onAbort: () => void;
  /** Whether query generation is currently in progress */
  isLoading: boolean;
  /** Number of messages in active conversation (0 means empty new chat state) */
  conversationLength: number;
  /** Rotating or static placeholder text */
  placeholderText?: string;
  /** Ref to the textarea element for programmatic focus / selection */
  textareaRef?: React.RefObject<HTMLTextAreaElement | null>;

  // Suggestions state
  showSuggestions: boolean;
  setShowSuggestions: (show: boolean) => void;
  filteredSuggestions: DynamicSuggestion[];
  activeSuggestionIndex: number;
  setActiveSuggestionIndex: React.Dispatch<React.SetStateAction<number>>;

  // Attached sources
  selectedDocs: SourceDocument[];
  isDocReady: (doc: SourceDocument) => boolean;
  onRemoveAttachedDoc: (id: string) => void;
  onOpenSourcesDrawer?: () => void;

  // Add Source Menu (+ button)
  addSourceMenuOpen: 'input' | 'drawer' | null;
  setAddSourceMenuOpen: React.Dispatch<React.SetStateAction<'input' | 'drawer' | null>>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onOpenLibraryPicker: () => void;

  // Research Mode (Fast / Expert)
  parseMode: 'fast' | 'expert';
  setParseMode: (mode: 'fast' | 'expert') => void;
  isOnline: boolean;

  // Speech / Voice
  isListening: boolean;
  isVoiceSpeaking: boolean;
  voiceAudioLevels: number[];
  voiceDurationSec: number;
  formatVoiceDuration: (seconds: number) => string;
  onToggleVoice: () => void;
  onStopVoiceListening: () => void;
  voiceError: string | null;
  onDismissVoiceError: () => void;

  /** Optional custom class name applied to outer section */
  className?: string;
}

/**
 * QueryBox Component
 * Dedicated prompt and question input interface where the user submits research queries.
 *
 * Isolated from + button and mode controls (located in `../query-controls/`)
 * for easy modification, styling adjustments, and feature extensions.
 */
export const QueryBox: React.FC<QueryBoxProps> = ({
  query,
  onQueryChange,
  onSubmit,
  onAbort,
  isLoading,
  conversationLength,
  placeholderText = 'Ask any question..',
  textareaRef,
  showSuggestions,
  setShowSuggestions,
  filteredSuggestions,
  activeSuggestionIndex,
  setActiveSuggestionIndex,
  selectedDocs,
  isDocReady,
  onRemoveAttachedDoc,
  onOpenSourcesDrawer,
  addSourceMenuOpen,
  setAddSourceMenuOpen,
  fileInputRef,
  onFileUpload,
  onOpenLibraryPicker,
  parseMode,
  setParseMode,
  isOnline,
  isListening,
  isVoiceSpeaking,
  voiceAudioLevels,
  voiceDurationSec,
  formatVoiceDuration,
  onToggleVoice,
  onStopVoiceListening,
  voiceError,
  onDismissVoiceError,
  className = '',
}) => {
  return (
    <section
      data-purpose="rag-prompt-container"
      className={`transition-all duration-300 w-full ${
        addSourceMenuOpen === 'input' ? '-translate-y-2.5 sm:translate-y-0' : 'translate-y-0'
      } ${
        conversationLength > 0
          ? 'sticky bottom-[max(0.5rem,env(safe-area-inset-bottom))] sm:bottom-4 z-30 mt-auto'
          : 'relative mb-1 sm:mb-0'
      } ${className}`}
    >
      {/* Ambient Glow & Shimmer Sweep - Only visible on new chat / empty state (vanishes after first query) */}
      {conversationLength === 0 && (
        <div aria-hidden="true" className="query-aura-glow animate-in fade-in duration-300" />
      )}

      <div className="interactive-query-box">
        {conversationLength === 0 && <div aria-hidden="true" className="beam-shimmer-sweep" />}

        {/* Screen-reader accessible suggestions list (visually hidden to prevent UI clutter) */}
        {showSuggestions && filteredSuggestions.length > 0 && (
          <div
            id="query-suggestions-list"
            data-testid="query-suggestions-list"
            role="listbox"
            aria-label="Prompt Suggestions"
            className="sr-only"
          >
            {filteredSuggestions.map((item, sIdx) => {
              const isHighlighted = activeSuggestionIndex === sIdx;
              return (
                <div
                  key={item.query}
                  id={`query-suggestion-${sIdx}`}
                  data-testid={`query-suggestion-item-${sIdx}`}
                  role="option"
                  aria-selected={isHighlighted}
                  tabIndex={-1}
                  onClick={() => {
                    onQueryChange(item.query);
                    setShowSuggestions(false);
                    setActiveSuggestionIndex(-1);
                    textareaRef?.current?.focus();
                  }}
                  onMouseEnter={() => setActiveSuggestionIndex(sIdx)}
                >
                  <span>{item.query}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Mobile Attached Sources: Floating chip strip cleanly placed ABOVE the WhatsApp question box */}
        <AttachedDocChips
          selectedDocs={selectedDocs}
          isDocReady={isDocReady}
          onRemoveDoc={onRemoveAttachedDoc}
          variant="mobile"
        />

        {/* WhatsApp-Style Input Bar on Mobile / Full RAG Card on Desktop */}
        <div
          className={`glass-input-container rounded-[26px] sm:rounded-2xl flex flex-row items-center sm:flex-col sm:items-stretch sm:justify-between relative z-10 transition-colors duration-200 border border-slate-300/90 dark:border-white/[0.08] focus-within:ring-2 focus-within:ring-indigo-500/30 dark:focus-within:ring-indigo-400/40 px-2 py-1 sm:p-3 gap-1 sm:gap-2 ${
            conversationLength === 0
              ? 'min-h-[44px] sm:min-h-[120px]'
              : 'min-h-[44px] sm:min-h-[58px] shadow-lg dark:shadow-2xl backdrop-blur-2xl'
          }`}
        >
          <div
            className={`order-2 sm:order-1 w-full flex-1 min-w-0 px-1 relative z-20 no-scrollbar ${
              conversationLength === 0 ? 'py-0.5 sm:pt-1 sm:pb-3' : 'py-0.5 sm:pt-0 sm:pb-0.5'
            }`}
          >
            {/* Real-time Voice Listening Floating Badge */}
            {isListening && (
              <div className="absolute -top-7 sm:-top-7.5 left-1 flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-900/90 dark:bg-white/95 text-white dark:text-slate-900 text-[11px] font-medium shadow-md animate-in fade-in slide-in-from-bottom-1 duration-150 pointer-events-none max-w-[88%] truncate z-30">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping shrink-0" />
                <span className="shrink-0 text-rose-300 dark:text-rose-600 font-semibold">
                  Listening:
                </span>
                <span className="truncate opacity-90">
                  {query.trim() || 'Speak your question...'}
                </span>
              </div>
            )}

            {conversationLength === 0 && !query && (
              <div
                onClick={() => textareaRef?.current?.focus()}
                className="absolute top-1 left-1 right-2 pointer-events-none select-none text-[13px] sm:text-base leading-snug sm:leading-relaxed font-normal overflow-hidden whitespace-nowrap text-ellipsis"
                aria-hidden="true"
              >
                {isListening ? (
                  <span className="text-rose-500 dark:text-rose-400 font-medium animate-pulse flex items-center gap-1.5">
                    <span className="inline-block w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                    Listening... Speak your research inquiry
                  </span>
                ) : (
                  <>
                    <span className="animated-ask-placeholder">{placeholderText}</span>
                    <span className="hidden sm:inline-block w-[2px] h-[1.15em] bg-indigo-500/85 dark:bg-indigo-400/90 ml-0.5 animated-cursor-blink align-middle rounded-full" />
                  </>
                )}
              </div>
            )}
            <textarea
              ref={textareaRef}
              value={query}
              role="combobox"
              aria-label="Ask a research inquiry (Cmd/Ctrl + K to focus)"
              aria-expanded={showSuggestions}
              aria-autocomplete="list"
              aria-controls="query-suggestions-list"
              aria-activedescendant={
                showSuggestions && activeSuggestionIndex >= 0
                  ? `query-suggestion-${activeSuggestionIndex}`
                  : undefined
              }
              onChange={(e) => {
                onQueryChange(e.target.value);
                if (!showSuggestions && e.target.value.trim()) {
                  setShowSuggestions(true);
                }
              }}
              onFocus={() => {
                if (conversationLength === 0 || query.length > 0) {
                  setShowSuggestions(true);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'ArrowDown') {
                  if (filteredSuggestions.length > 0) {
                    e.preventDefault();
                    if (!showSuggestions) {
                      setShowSuggestions(true);
                      setActiveSuggestionIndex(0);
                    } else {
                      setActiveSuggestionIndex((prev) =>
                        prev < filteredSuggestions.length - 1 ? prev + 1 : 0
                      );
                    }
                  }
                } else if (e.key === 'ArrowUp') {
                  if (filteredSuggestions.length > 0) {
                    e.preventDefault();
                    if (!showSuggestions) {
                      setShowSuggestions(true);
                      setActiveSuggestionIndex(filteredSuggestions.length - 1);
                    } else {
                      setActiveSuggestionIndex((prev) =>
                        prev > 0 ? prev - 1 : filteredSuggestions.length - 1
                      );
                    }
                  }
                } else if (e.key === 'Enter' && !e.shiftKey) {
                  if (
                    showSuggestions &&
                    activeSuggestionIndex >= 0 &&
                    activeSuggestionIndex < filteredSuggestions.length
                  ) {
                    e.preventDefault();
                    const selected = filteredSuggestions[activeSuggestionIndex];
                    onQueryChange(selected.query);
                    setShowSuggestions(false);
                    setActiveSuggestionIndex(-1);
                  } else {
                    e.preventDefault();
                    if (isLoading) {
                      onAbort();
                    } else {
                      setShowSuggestions(false);
                      setActiveSuggestionIndex(-1);
                      onSubmit();
                    }
                  }
                } else if (e.key === 'Escape') {
                  if (showSuggestions) {
                    e.preventDefault();
                    setShowSuggestions(false);
                    setActiveSuggestionIndex(-1);
                  }
                }
              }}
              className={`w-full bg-transparent border-0 resize-none text-[13.5px] sm:text-[clamp(0.875rem,2vw,1rem)] text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-0 py-0.5 px-0 leading-snug sm:leading-relaxed font-normal focus:outline-none overflow-y-auto no-scrollbar scrollbar-none [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden ${
                conversationLength === 0
                  ? 'min-h-[22px] sm:min-h-[52px]'
                  : 'min-h-[22px] sm:min-h-[24px]'
              } max-h-[96px] sm:max-h-[140px]`}
              style={{
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
              }}
              placeholder={
                isListening
                  ? 'Listening... Speak your research inquiry'
                  : conversationLength === 0
                    ? ''
                    : 'Ask a follow-up inquiry...'
              }
              rows={1}
            />
          </div>

          <div
            className={`contents sm:flex sm:order-2 sm:w-full sm:items-center sm:justify-between sm:gap-2 relative z-20 ${
              conversationLength === 0 ? 'sm:pt-1.5' : 'sm:pt-1'
            }`}
          >
            {/* Attachments Section: On mobile, only + button on the left (order-1). On desktop, + button and desktop chips on lower-left */}
            <div className="order-1 sm:order-none flex items-center gap-1.5 sm:gap-2 shrink-0 select-none">
              <AddSourceButton
                isOpen={addSourceMenuOpen === 'input'}
                onToggle={() => setAddSourceMenuOpen((prev) => (prev === 'input' ? null : 'input'))}
                onClose={() => setAddSourceMenuOpen(null)}
                fileInputRef={fileInputRef}
                onFileUpload={onFileUpload}
                onOpenLibraryPicker={onOpenLibraryPicker}
                parseMode={parseMode}
                onSelectMode={setParseMode}
                conversationLength={conversationLength}
              />
              <AttachedDocChips
                selectedDocs={selectedDocs}
                isDocReady={isDocReady}
                onRemoveDoc={onRemoveAttachedDoc}
                onOpenDrawer={onOpenSourcesDrawer}
                conversationLength={conversationLength}
                variant="desktop"
              />
            </div>

            {/* Right / Lower Side: Fast/Expert, Mic, and Enter actions kept in the same place, fully responsive */}
            <div className="order-3 sm:order-none flex items-center justify-end space-x-1 sm:space-x-2 shrink-0 ml-auto">
              <FastExpertToggle
                parseMode={parseMode}
                onSelectMode={setParseMode}
                isOnline={isOnline}
                variant="desktop"
              />

              <VoiceInputButton
                isListening={isListening}
                isVoiceSpeaking={isVoiceSpeaking}
                voiceAudioLevels={voiceAudioLevels}
                voiceDurationSec={voiceDurationSec}
                hasSpeechContent={query.trim().length > 0}
                onToggleVoice={onToggleVoice}
                onSubmitVoice={() => {
                  onStopVoiceListening();
                  onSubmit();
                }}
                formatVoiceDuration={formatVoiceDuration}
              />

              {/* Right-Aligned Action: Submit / Stop Button (Hidden until user types something, attaches sources, or while loading) */}
              {(query.trim().length > 0 || selectedDocs.length > 0 || isLoading) && (
                <button
                  type="button"
                  onClick={isLoading ? onAbort : onSubmit}
                  title={isLoading ? 'Stop generating' : 'Send question'}
                  aria-label={isLoading ? 'Stop generating query process' : 'Execute RAG Query'}
                  className={`${
                    conversationLength === 0
                      ? 'w-7.5 h-7.5 sm:w-8 sm:h-8'
                      : 'w-6.5 h-6.5 sm:w-8 sm:h-8'
                  } rounded-full transition-all flex items-center justify-center shrink-0 bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-slate-200 shadow-md cursor-pointer active:scale-95 animate-in fade-in zoom-in-90 duration-150`}
                >
                  {isLoading ? (
                    <div className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-xs bg-white dark:bg-black" />
                  ) : (
                    <svg
                      className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white dark:text-black"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        d="M5 10l7-7m0 0l7 7m-7-7v18"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2.5"
                      />
                    </svg>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Voice query error message banner if mic access fails */}
        {voiceError && (
          <div className="mt-2 px-3 py-1.5 text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 rounded-xl flex items-center justify-between gap-2 animate-in fade-in duration-150">
            <div className="flex items-center gap-1.5 min-w-0">
              <svg
                className="w-4 h-4 text-rose-500 shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <span>{voiceError}</span>
            </div>
            <button
              type="button"
              onClick={onDismissVoiceError}
              className="p-1 text-rose-500 hover:text-rose-700 dark:hover:text-rose-200 rounded-md cursor-pointer"
              aria-label="Dismiss error"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        )}
      </div>
    </section>
  );
};
