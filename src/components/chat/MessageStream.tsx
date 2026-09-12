import React from 'react';
import { AnswerMarkdown } from './AnswerMarkdown';
import { CitationBadge } from '../citations/CitationBadge';
import { ExportResponseDropdown } from './ExportResponseDropdown';
import { ActiveSubgraphCard } from '../graph/ActiveSubgraphCard';
import { Citation } from '../../types';

export interface StreamMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp?: string;
  citations?: Citation[];
  subgraph?: {
    nodes?: any[];
    edges?: any[];
  };
  query_type?: string;
  cypher_status?: string;
  traceability_score?: number;
}

export interface MessageStreamProps {
  messages: StreamMessage[];
  speakingMessageId?: string | null;
  onSpeak?: (text: string, id: string) => void;
  onCopy?: (text: string, id: string) => void;
  onSelectGraphNode?: (node: any) => void;
  copiedId?: string | null;
  className?: string;
}

export const MessageStream: React.FC<MessageStreamProps> = ({
  messages,
  speakingMessageId,
  onSpeak,
  onCopy,
  onSelectGraphNode,
  copiedId,
  className = '',
}) => {
  if (messages.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="message-stream"
      className={`space-y-6 max-w-4xl mx-auto px-3 sm:px-6 py-4 ${className}`}
    >
      {messages.map((msg) => {
        const isAssistant = msg.role === 'assistant';
        const isSpeaking = speakingMessageId === msg.id;
        const isCopied = copiedId === msg.id;

        return (
          <div
            key={msg.id}
            data-testid={`chat-message-${msg.id}`}
            className={`flex gap-3 sm:gap-4 ${
              isAssistant ? 'items-start' : 'justify-end'
            }`}
          >
            {/* Assistant Avatar */}
            {isAssistant && (
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm mt-0.5">
                R
              </div>
            )}

            {/* Message Body Bubble */}
            <div
              className={`min-w-0 max-w-full ${
                isAssistant
                  ? 'flex-1 space-y-3 bg-white/70 dark:bg-white/[0.03] p-4 sm:p-5 rounded-2xl border border-slate-200/80 dark:border-white/10 shadow-xs'
                  : 'bg-indigo-600 text-white px-4 py-2.5 rounded-2xl max-w-[85%] sm:max-w-[75%] shadow-sm'
              }`}
            >
              {isAssistant ? (
                <>
                  {/* Markdown Answer */}
                  <AnswerMarkdown content={msg.text} citations={msg.citations} showCitations={true} />

                  {/* Citations Row */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-3 border-t border-slate-200/60 dark:border-white/10 flex flex-wrap gap-1.5 items-center">
                      <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mr-1">
                        Sources:
                      </span>
                      {msg.citations.map((c, i) => (
                        <CitationBadge
                          key={i}
                          index={i + 1}
                          citation={c}
                        />
                      ))}
                    </div>
                  )}

                  {/* Active Subgraph Visualization Card */}
                  {msg.subgraph && (
                    <ActiveSubgraphCard
                      nodes={msg.subgraph.nodes}
                      edges={msg.subgraph.edges}
                      queryType={msg.query_type}
                      cypherStatus={msg.cypher_status}
                      traceabilityScore={msg.traceability_score}
                      onSelectNode={onSelectGraphNode}
                    />
                  )}

                  {/* Message Action Bar */}
                  <div className="flex items-center justify-between pt-2 text-slate-400">
                    <div className="flex items-center gap-1">
                      {onCopy && (
                        <button
                          type="button"
                          onClick={() => onCopy(msg.text, msg.id)}
                          title="Copy response"
                          className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/10 transition-colors cursor-pointer text-xs flex items-center gap-1"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          <span>{isCopied ? 'Copied' : 'Copy'}</span>
                        </button>
                      )}

                      {onSpeak && (
                        <button
                          type="button"
                          onClick={() => onSpeak(msg.text, msg.id)}
                          title={isSpeaking ? 'Stop reading' : 'Read aloud'}
                          className={`p-1 rounded transition-colors cursor-pointer text-xs flex items-center gap-1 ${
                            isSpeaking
                              ? 'text-indigo-600 dark:text-indigo-400'
                              : 'text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/10'
                          }`}
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                          </svg>
                          <span>{isSpeaking ? 'Stop' : 'Listen'}</span>
                        </button>
                      )}
                    </div>

                    <ExportResponseDropdown
                      query="Research Inquiry"
                      answerText={msg.text}
                      response={{
                        grounded_answer: msg.text,
                        citations: msg.citations,
                      }}
                    />
                  </div>
                </>
              ) : (
                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.text}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
