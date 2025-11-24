'use client';

import { useState } from 'react';
import { Episode } from '@/lib/types';

interface EpisodeViewProps {
  episode: Episode;
  episodeNumber: number;
}

// Helper function to clean up terminal output
function cleanTerminalOutput(text: string): string {
  // Collapse multiple consecutive newlines (more than 3) into just 2
  return text.replace(/\n{4,}/g, '\n\n');
}

// Helper function to truncate long text
function truncateText(text: string, maxLength: number = 800): { truncated: string; isTruncated: boolean } {
  if (text.length <= maxLength) {
    return { truncated: text, isTruncated: false };
  }

  // Find a good break point (end of line or word)
  let breakPoint = maxLength;
  const newlineIndex = text.lastIndexOf('\n', maxLength);
  if (newlineIndex > maxLength * 0.7) {
    breakPoint = newlineIndex;
  }

  return {
    truncated: text.substring(0, breakPoint),
    isTruncated: true
  };
}

export default function EpisodeView({ episode, episodeNumber }: EpisodeViewProps) {
  const [isExpanded, setIsExpanded] = useState(episodeNumber === 0);
  const [showFullExplanation, setShowFullExplanation] = useState(false);

  return (
    <div className="bg-white border-2 border-slate-200 rounded-xl overflow-hidden hover:border-blue-300 transition-all duration-200">
      <div
        className="p-4 bg-slate-50 cursor-pointer hover:bg-slate-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-md">
              {episodeNumber}
            </div>
            <h5 className="font-bold text-slate-900">Episode {episodeNumber}</h5>
          </div>
          <svg
            className={`w-5 h-5 text-slate-400 transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {isExpanded && (
        <div className="p-6 bg-white space-y-6 animate-fade-in">
          {episode.state_analysis && (
            <div className="border-l-4 border-blue-500 pl-4">
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                <h6 className="text-sm font-bold text-slate-900 uppercase tracking-wide">State Analysis</h6>
              </div>
              <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{episode.state_analysis}</p>
            </div>
          )}

          {episode.explanation && (() => {
            const cleanedExplanation = cleanTerminalOutput(episode.explanation);
            const { truncated, isTruncated } = truncateText(cleanedExplanation);
            const displayText = showFullExplanation ? cleanedExplanation : truncated;

            return (
              <div className="border-l-4 border-indigo-500 pl-4">
                <div className="flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h6 className="text-sm font-bold text-slate-900 uppercase tracking-wide">Terminal State</h6>
                </div>
                <div className="bg-slate-900 text-slate-200 p-4 rounded-lg overflow-x-auto border-2 border-slate-800 shadow-inner">
                  <pre className="text-xs font-mono leading-relaxed whitespace-pre-wrap">{displayText}</pre>
                </div>
                {isTruncated && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowFullExplanation(!showFullExplanation);
                    }}
                    className="mt-2 text-sm text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
                  >
                    {showFullExplanation ? (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                        Show less
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                        Show full terminal output ({cleanedExplanation.length} characters)
                      </>
                    )}
                  </button>
                )}
              </div>
            );
          })()}

          {episode.commands && episode.commands.trim() && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <h6 className="text-sm font-bold text-slate-900 uppercase tracking-wide">Commands</h6>
              </div>
              <div className="relative">
                <pre className="bg-slate-900 text-emerald-400 p-4 rounded-lg overflow-x-auto text-sm font-mono leading-relaxed border-2 border-slate-800 shadow-inner">
                  {episode.commands}
                </pre>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigator.clipboard.writeText(episode.commands || '');
                  }}
                  className="absolute top-2 right-2 p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors"
                  title="Copy to clipboard"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

