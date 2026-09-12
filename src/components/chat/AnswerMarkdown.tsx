import React, { useState } from 'react';
import { Citation } from '../../types';
import { CitationBadge } from '../citations/CitationBadge';
import { sanitizeStreamText } from '../../utils/sanitizeStreamText';
import { cleanRagResponseText } from '../../utils/citationParser';

export interface AnswerMarkdownProps {
  content: string;
  citations?: Citation[];
  showCitations?: boolean;
  className?: string;
}

interface CodeBlockProps {
  code: string;
  language?: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="my-3.5 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-900 text-slate-100 shadow-2xs">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-800/80 border-b border-slate-700/60 text-[11px] font-mono text-slate-400">
        <span className="font-medium tracking-wide uppercase">{language || 'code'}</span>
        <button
          onClick={handleCopy}
          className="text-xs text-slate-400 hover:text-white transition-colors cursor-pointer px-1.5 py-0.5 rounded hover:bg-slate-700/60"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto font-mono text-[12.5px] leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
};

type Block =
  | { type: 'heading'; level: 1 | 2 | 3 | 4; text: string }
  | { type: 'code'; language: string; code: string }
  | { type: 'table'; headers: string[]; alignments: string[]; rows: string[][] }
  | { type: 'blockquote'; text: string }
  | { type: 'ordered-list'; items: { num: string; text: string; indent: number }[] }
  | { type: 'unordered-list'; items: { text: string; indent: number }[] }
  | { type: 'hr' }
  | { type: 'callout'; variant: 'info' | 'warning'; text: string }
  | { type: 'paragraph'; text: string };

function parseMarkdownBlocks(text: string): Block[] {
  const lines = text.split('\n');
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // 2. Fenced Code Block: ```lang
    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length && lines[i].trim().startsWith('```')) {
        i++;
      }
      blocks.push({
        type: 'code',
        language,
        code: codeLines.join('\n'),
      });
      continue;
    }

    // 3. Horizontal Rule: ---, ***, ___
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push({ type: 'hr' });
      i++;
      continue;
    }

    // 4. Headings: #, ##, ###, ####
    if (trimmed.startsWith('#')) {
      const match = trimmed.match(/^(#{1,4})\s+(.*)$/);
      if (match) {
        const level = match[1].length as 1 | 2 | 3 | 4;
        blocks.push({
          type: 'heading',
          level,
          text: match[2],
        });
        i++;
        continue;
      }
    }

    // 5. Blockquote: > text
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i++;
      }
      blocks.push({
        type: 'blockquote',
        text: quoteLines.join(' '),
      });
      continue;
    }

    // 6. Markdown Table: starts with | and followed by separator
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && i + 1 < lines.length) {
      const nextLine = lines[i + 1].trim();
      if (/^\|?(\s*:?-+:?\s*\|)+\s*$/.test(nextLine)) {
        const headers = trimmed.slice(1, -1).split('|').map((s) => s.trim());
        const alignSpecs = nextLine.slice(1, -1).split('|').map((s) => s.trim());
        const alignments = alignSpecs.map((spec) => {
          if (spec.startsWith(':') && spec.endsWith(':')) return 'text-center';
          if (spec.endsWith(':')) return 'text-right';
          return 'text-left';
        });

        i += 2;
        const rows: string[][] = [];
        while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
          const cells = lines[i].trim().slice(1, -1).split('|').map((s) => s.trim());
          rows.push(cells);
          i++;
        }

        blocks.push({
          type: 'table',
          headers,
          alignments,
          rows,
        });
        continue;
      }
    }

    // 7. Ordered List: 1. Item
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: { num: string; text: string; indent: number }[] = [];
      while (i < lines.length) {
        const currentLine = lines[i];
        const match = currentLine.match(/^(\s*)(\d+)\.\s+(.*)$/);
        if (match) {
          const indent = Math.floor(match[1].length / 2);
          items.push({
            num: match[2],
            text: match[3],
            indent,
          });
          i++;
        } else if (items.length > 0 && currentLine.trim() && (currentLine.startsWith('   ') || currentLine.startsWith('\t') || currentLine.startsWith('  '))) {
          items[items.length - 1].text += '\n' + currentLine.trim();
          i++;
        } else {
          break;
        }
      }
      blocks.push({
        type: 'ordered-list',
        items,
      });
      continue;
    }

    // 8. Unordered List: - item or * item
    if (/^\s*([*\-•])\s+/.test(line)) {
      const items: { text: string; indent: number }[] = [];
      while (i < lines.length) {
        const currentLine = lines[i];
        const match = currentLine.match(/^(\s*)([*\-•])\s+(.*)$/);
        if (match) {
          const indent = Math.floor(match[1].length / 2);
          items.push({
            text: match[3],
            indent,
          });
          i++;
        } else if (items.length > 0 && currentLine.trim() && (currentLine.startsWith('   ') || currentLine.startsWith('\t') || currentLine.startsWith('  '))) {
          items[items.length - 1].text += '\n' + currentLine.trim();
          i++;
        } else {
          break;
        }
      }
      blocks.push({
        type: 'unordered-list',
        items,
      });
      continue;
    }

    // 9. Callouts
    if (/^\*\*(Warning|Caution|Alert|Important):\*\*/i.test(trimmed)) {
      blocks.push({
        type: 'callout',
        variant: 'warning',
        text: trimmed,
      });
      i++;
      continue;
    }

    if (/^\*\*(Note|Key Takeaway|Finding|Summary|Takeaway):\*\*/i.test(trimmed)) {
      blocks.push({
        type: 'callout',
        variant: 'info',
        text: trimmed,
      });
      i++;
      continue;
    }

    // 10. Standard Paragraph: group contiguous non-blank lines
    const paraLines: string[] = [trimmed];
    i++;
    while (i < lines.length) {
      const nextLine = lines[i];
      const nextTrimmed = nextLine.trim();
      if (!nextTrimmed) break;
      if (
        nextTrimmed.startsWith('#') ||
        nextTrimmed.startsWith('```') ||
        nextTrimmed.startsWith('>') ||
        /^(\-{3,}|\*{3,}|_{3,})$/.test(nextTrimmed) ||
        /^\s*\d+\.\s+/.test(nextLine) ||
        /^\s*([*\-•])\s+/.test(nextLine) ||
        (nextTrimmed.startsWith('|') && nextTrimmed.endsWith('|')) ||
        /^\*\*(Warning|Caution|Alert|Important|Note|Key Takeaway|Finding|Summary|Takeaway):\*\*/i.test(nextTrimmed)
      ) {
        break;
      }
      paraLines.push(nextTrimmed);
      i++;
    }

    blocks.push({
      type: 'paragraph',
      text: paraLines.join('\n'),
    });
  }

  return blocks;
}

export const AnswerMarkdown: React.FC<AnswerMarkdownProps> = ({
  content,
  citations = [],
  showCitations = false,
  className = '',
}) => {
  if (!content) return null;

  // Sanitize any raw JSON token fragments or leaked stream tokens
  const sanitized = sanitizeStreamText(content);

  // Clean RAG artifacts, unpack verbose in-text citations, and normalize layout
  const { cleanText: preparedText, citations: enrichedCitations } = cleanRagResponseText(
    sanitized,
    citations
  );

  // If showCitations is false, strip bracketed markers like [1], [2] from the content
  const cleanContent = showCitations ? preparedText : preparedText.replace(/\s*\[\d+\]/g, '');

  const citationMap = new Map<number, Citation>();
  if (showCitations && enrichedCitations) {
    for (const c of enrichedCitations) {
      citationMap.set(c.citation_index, c);
    }
  }

  const renderInline = (text: string, keyPrefix: string): React.ReactNode => {
    if (!text) return null;

    // Tokenize text into inline elements
    const regex = /(`[^`]+`|\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|__[^_]+__|\[\d+\]|\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]+)\)|\*[^*\n]+\*|_[^_\n]+_)/g;

    const elements: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    let elementIdx = 0;

    while ((match = regex.exec(text)) !== null) {
      const matchStart = match.index;
      const matchEnd = regex.lastIndex;
      const matchedStr = match[0];

      if (matchStart > lastIndex) {
        elements.push(
          <span key={`${keyPrefix}-txt-${elementIdx++}`}>
            {text.substring(lastIndex, matchStart)}
          </span>
        );
      }

      // Inline code
      if (matchedStr.startsWith('`') && matchedStr.endsWith('`')) {
        elements.push(
          <code
            key={`${keyPrefix}-code-${elementIdx++}`}
            className="px-1.5 py-0.5 mx-0.5 rounded-md bg-slate-100 dark:bg-white/[0.08] text-indigo-600 dark:text-indigo-300 font-mono text-[12.5px] border border-slate-200/80 dark:border-white/10"
          >
            {matchedStr.slice(1, -1)}
          </code>
        );
      }
      // Bold Italic
      else if (matchedStr.startsWith('***') && matchedStr.endsWith('***')) {
        elements.push(
          <strong
            key={`${keyPrefix}-bi-${elementIdx++}`}
            className="font-bold italic text-slate-900 dark:text-white"
          >
            {matchedStr.slice(3, -3)}
          </strong>
        );
      }
      // Bold
      else if (
        (matchedStr.startsWith('**') && matchedStr.endsWith('**')) ||
        (matchedStr.startsWith('__') && matchedStr.endsWith('__'))
      ) {
        const inner = matchedStr.slice(2, -2);
        elements.push(
          <strong
            key={`${keyPrefix}-b-${elementIdx++}`}
            className="font-semibold text-slate-900 dark:text-white"
          >
            {renderInline(inner, `${keyPrefix}-b-${elementIdx}`)}
          </strong>
        );
      }
      // Citation Badge
      else if (showCitations && /^\[\d+\]$/.test(matchedStr)) {
        const citIdx = parseInt(matchedStr.slice(1, -1), 10);
        const matchedCit = citationMap.get(citIdx);
        elements.push(
          <CitationBadge
            key={`${keyPrefix}-cit-${elementIdx++}`}
            index={citIdx}
            citation={matchedCit}
          />
        );
      }
      // Link
      else if (match[2] && match[3]) {
        elements.push(
          <a
            key={`${keyPrefix}-link-${elementIdx++}`}
            href={match[3]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline inline-flex items-center gap-0.5"
          >
            {match[2]}
          </a>
        );
      }
      // Italic
      else if (
        (matchedStr.startsWith('*') && matchedStr.endsWith('*')) ||
        (matchedStr.startsWith('_') && matchedStr.endsWith('_'))
      ) {
        elements.push(
          <em
            key={`${keyPrefix}-em-${elementIdx++}`}
            className="italic text-slate-700 dark:text-slate-300"
          >
            {matchedStr.slice(1, -1)}
          </em>
        );
      } else {
        elements.push(
          <span key={`${keyPrefix}-raw-${elementIdx++}`}>{matchedStr}</span>
        );
      }

      lastIndex = matchEnd;
    }

    if (lastIndex < text.length) {
      elements.push(
        <span key={`${keyPrefix}-txt-${elementIdx++}`}>
          {text.substring(lastIndex)}
        </span>
      );
    }

    return <React.Fragment key={keyPrefix}>{elements}</React.Fragment>;
  };

  const blocks = parseMarkdownBlocks(cleanContent);

  return (
    <div className={`space-y-3 leading-relaxed text-slate-800 dark:text-slate-200 font-sans text-[14.5px] ${className}`}>
      {blocks.map((block, idx) => {
        switch (block.type) {
          case 'heading': {
            if (block.level === 1) {
              return (
                <h2
                  key={idx}
                  className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-6 mb-3 pb-2.5 border-b border-slate-200/80 dark:border-white/10 flex items-center gap-2.5"
                >
                  <span className="w-1.5 h-5 rounded-full bg-indigo-600 dark:bg-indigo-400 inline-block shrink-0" />
                  <span>{renderInline(block.text, `h1-${idx}`)}</span>
                </h2>
              );
            }
            if (block.level === 2) {
              return (
                <h3
                  key={idx}
                  className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mt-5 mb-2.5 flex items-center gap-2"
                >
                  <span className="w-1 h-4 rounded-full bg-indigo-500 dark:bg-indigo-400 inline-block shrink-0" />
                  <span>{renderInline(block.text, `h2-${idx}`)}</span>
                </h3>
              );
            }
            if (block.level === 3) {
              return (
                <h4
                  key={idx}
                  className="text-[15.5px] font-semibold text-indigo-700 dark:text-indigo-300 mt-4 mb-2 flex items-center gap-1.5"
                >
                  <span>{renderInline(block.text, `h3-${idx}`)}</span>
                </h4>
              );
            }
            return (
              <h5
                key={idx}
                className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mt-3 mb-1"
              >
                <span>{renderInline(block.text, `h4-${idx}`)}</span>
              </h5>
            );
          }

          case 'ordered-list': {
            return (
              <ol key={idx} className="space-y-2.5 my-3 list-none p-0">
                {block.items.map((item, itemIdx) => (
                  <li
                    key={itemIdx}
                    className={`flex items-start gap-2.5 ${
                      item.indent > 0 ? 'ml-5 sm:ml-7 text-[13.5px]' : 'text-[14.5px]'
                    }`}
                  >
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-50 dark:bg-indigo-950/70 text-indigo-600 dark:text-indigo-400 border border-indigo-200/70 dark:border-indigo-800/60 text-[11px] font-bold flex items-center justify-center font-mono mt-0.5 shadow-2xs">
                      {item.num}
                    </span>
                    <div className="flex-1 min-w-0 leading-relaxed text-slate-700 dark:text-slate-200 whitespace-pre-line">
                      {renderInline(item.text, `ol-${idx}-${itemIdx}`)}
                    </div>
                  </li>
                ))}
              </ol>
            );
          }

          case 'unordered-list': {
            return (
              <ul key={idx} className="space-y-3.5 my-3 list-none p-0">
                {block.items.map((item, itemIdx) => {
                  const headerMatch = item.text.match(/^(\*\*[^*]+\*\*(?:\s*\[\d+\])?)\s*[:—–-]?\s*\n+([\s\S]*)$/);

                  if (item.indent > 0) {
                    return (
                      <li
                        key={itemIdx}
                        className="flex items-start gap-2 ml-5 sm:ml-7 text-[13.5px] leading-relaxed text-slate-600 dark:text-slate-300"
                      >
                        <span className="flex-shrink-0 w-1.5 h-1.5 rounded-xs border border-indigo-400/80 dark:border-indigo-400/60 mt-2" />
                        <div className="flex-1 min-w-0 whitespace-pre-line">
                          {renderInline(item.text, `ul-${idx}-${itemIdx}`)}
                        </div>
                      </li>
                    );
                  }

                  if (headerMatch) {
                    return (
                      <li
                        key={itemIdx}
                        className="flex items-start gap-2.5 text-[14.5px] leading-relaxed text-slate-700 dark:text-slate-200"
                      >
                        <span className="flex-shrink-0 w-2 h-2 rounded-full bg-indigo-500 dark:bg-indigo-400 mt-2 shadow-2xs" />
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-slate-900 dark:text-slate-100 flex flex-wrap items-center gap-1.5 leading-snug">
                            {renderInline(headerMatch[1], `ul-h-${idx}-${itemIdx}`)}
                          </div>
                          {headerMatch[2] && (
                            <div className="mt-1.5 text-slate-700 dark:text-slate-300 text-[13.5px] leading-relaxed whitespace-pre-line pl-3 border-l-2 border-indigo-200/80 dark:border-indigo-800/60 bg-slate-50/60 dark:bg-white/[0.015] py-1.5 rounded-r-lg">
                              {renderInline(headerMatch[2], `ul-b-${idx}-${itemIdx}`)}
                            </div>
                          )}
                        </div>
                      </li>
                    );
                  }

                  return (
                    <li
                      key={itemIdx}
                      className="flex items-start gap-2.5 text-[14.5px] leading-relaxed text-slate-700 dark:text-slate-200"
                    >
                      <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-indigo-500 dark:bg-indigo-400 mt-2 shadow-2xs" />
                      <div className="flex-1 min-w-0 whitespace-pre-line">
                        {renderInline(item.text, `ul-${idx}-${itemIdx}`)}
                      </div>
                    </li>
                  );
                })}
              </ul>
            );
          }

          case 'blockquote': {
            return (
              <blockquote
                key={idx}
                className="border-l-3 border-indigo-500/80 dark:border-indigo-400 pl-3.5 py-2 my-3 bg-indigo-50/40 dark:bg-white/[0.02] rounded-r-xl text-slate-600 dark:text-slate-300 italic text-[14px] leading-relaxed"
              >
                {renderInline(block.text, `bq-${idx}`)}
              </blockquote>
            );
          }

          case 'callout': {
            if (block.variant === 'warning') {
              return (
                <div
                  key={idx}
                  className="my-3 p-3.5 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-800/60 text-slate-800 dark:text-slate-200 text-[14px] leading-relaxed shadow-2xs flex items-start gap-2.5"
                >
                  <span className="text-amber-600 dark:text-amber-400 font-bold shrink-0 mt-0.5">⚠</span>
                  <div className="flex-1 min-w-0">{renderInline(block.text, `callout-warn-${idx}`)}</div>
                </div>
              );
            }
            return (
              <div
                key={idx}
                className="my-3 p-3.5 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200/80 dark:border-indigo-800/60 text-slate-800 dark:text-slate-200 text-[14px] leading-relaxed shadow-2xs flex items-start gap-2.5"
              >
                <span className="text-indigo-600 dark:text-indigo-400 font-bold shrink-0 mt-0.5">ℹ</span>
                <div className="flex-1 min-w-0">{renderInline(block.text, `callout-info-${idx}`)}</div>
              </div>
            );
          }

          case 'code': {
            return <CodeBlock key={idx} code={block.code} language={block.language} />;
          }

          case 'table': {
            return (
              <div
                key={idx}
                className="overflow-x-auto my-4 rounded-xl border border-slate-200/80 dark:border-white/10 shadow-2xs"
              >
                <table className="w-full text-left text-xs sm:text-sm border-collapse">
                  <thead className="bg-slate-100/80 dark:bg-white/[0.05] border-b border-slate-200 dark:border-white/10 text-slate-800 dark:text-slate-200 font-semibold">
                    <tr>
                      {block.headers.map((h, hIdx) => (
                        <th
                          key={hIdx}
                          className={`px-4 py-2.5 font-semibold text-slate-900 dark:text-slate-100 ${
                            block.alignments[hIdx] || 'text-left'
                          }`}
                        >
                          {renderInline(h, `th-${idx}-${hIdx}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {block.rows.map((row, rIdx) => (
                      <tr
                        key={rIdx}
                        className="hover:bg-slate-50/60 dark:hover:bg-white/[0.02] transition-colors"
                      >
                        {row.map((cell, cIdx) => (
                          <td
                            key={cIdx}
                            className={`px-4 py-2 text-slate-700 dark:text-slate-300 ${
                              block.alignments[cIdx] || 'text-left'
                            }`}
                          >
                            {renderInline(cell, `td-${idx}-${rIdx}-${cIdx}`)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }

          case 'hr': {
            return <hr key={idx} className="my-5 border-t border-slate-200/80 dark:border-white/10" />;
          }

          case 'paragraph':
          default: {
            return (
              <p
                key={idx}
                className="text-[14.5px] leading-relaxed text-slate-700 dark:text-slate-200 my-2.5 whitespace-pre-line"
              >
                {renderInline(block.text, `p-${idx}`)}
              </p>
            );
          }
        }
      })}
    </div>
  );
};
