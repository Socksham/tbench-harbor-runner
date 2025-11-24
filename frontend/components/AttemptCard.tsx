'use client';

import type { JSX } from 'react';
import { Run } from '@/lib/api';
import { ParsedRunResult } from '@/lib/types';
import { parseRunResult } from '@/lib/parsers';
import EpisodeView from './EpisodeView';
import TestCaseList from './TestCaseList';
import LogViewer from './LogViewer';

interface AttemptCardProps {
  run: Run;
  isExpanded: boolean;
  onToggle: () => void;
}

export default function AttemptCard({ run, isExpanded, onToggle }: AttemptCardProps) {
  const parsed = parseRunResult(run);
  const alertStyles: Record<
    'info' | 'warning' | 'error',
    { bg: string; border: string; icon: JSX.Element; text: string }
  > = {
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      text: 'text-blue-800',
      icon: (
        <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
        </svg>
      ),
    },
    warning: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-900',
      icon: (
        <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.29 3.86L1.82 18a1 1 0 00.86 1.5h18.64a1 1 0 00.86-1.5L12.71 3.86a1 1 0 00-1.72 0zM12 9v4m0 4h.01" />
        </svg>
      ),
    },
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-900',
      icon: (
        <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 5a7 7 0 11-7 7 7 7 0 017-7z" />
        </svg>
      ),
    },
  };
  
  // Determine status text and styling based on parsed status
  let statusText: string;
  let statusColor: string;
  let statusBg: string;
  let statusBorder: string;
  let badgeColor: string;
  let badgeBg: string;
  let badgeBorder: string;
  
  if (parsed.status === 'passed') {
    statusText = 'AGENT PASSED';
    badgeColor = 'text-green-800';
    badgeBg = 'bg-green-100';
    badgeBorder = 'border-green-300';
    statusColor = 'bg-green-600';
  } else if (parsed.status === 'running') {
    statusText = 'RUNNING';
    badgeColor = 'text-yellow-800';
    badgeBg = 'bg-yellow-100';
    badgeBorder = 'border-yellow-300';
    statusColor = 'bg-yellow-600';
  } else if (parsed.status === 'pending') {
    statusText = 'PENDING';
    badgeColor = 'text-slate-800';
    badgeBg = 'bg-slate-100';
    badgeBorder = 'border-slate-300';
    statusColor = 'bg-slate-600';
  } else {
    statusText = 'AGENT FAILED';
    badgeColor = 'text-red-800';
    badgeBg = 'bg-red-100';
    badgeBorder = 'border-red-300';
    statusColor = 'bg-red-600';
  }
  
  const isPassed = parsed.status === 'passed';
  const isRunning = parsed.status === 'running';
  const isPending = parsed.status === 'pending';
  const passRate = parsed.tests_total > 0 ? (parsed.tests_passed / parsed.tests_total) * 100 : 0;
  
  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-slate-200 overflow-hidden hover:shadow-xl transition-all duration-200">
      {/* Header */}
      <div
        className="p-6 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg shadow-md text-white ${statusColor} ${isRunning ? 'animate-pulse' : ''}`}>
              {run.run_number}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-xl font-bold text-slate-900 mb-1">Attempt {run.run_number}</h3>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wide border ${badgeBg} ${badgeColor} ${badgeBorder}`}>
                  {statusText}
                </span>
                {(parsed.status === 'passed' || parsed.status === 'failed') && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="font-medium">{parsed.tests_passed}/{parsed.tests_total} tests passed</span>
                    <span className="text-slate-400">({passRate.toFixed(1)}%)</span>
                  </div>
                )}
                {parsed.status === 'running' && (
                  <div className="flex items-center gap-2 text-sm text-yellow-600">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="font-medium">Running...</span>
                  </div>
                )}
                {parsed.status === 'pending' && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="font-medium">Waiting to start...</span>
                  </div>
                )}
                {parsed.episodes.length > 0 && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                    <span>{parsed.episodes.length} {parsed.episodes.length === 1 ? 'episode' : 'episodes'}</span>
                  </div>
                )}
              </div>
              {parsed.alerts.length > 0 && (
                <div className="w-full space-y-2 mt-3">
                  {parsed.alerts.map((alert, idx) => {
                    const style = alertStyles[alert.type];
                    return (
                      <div
                        key={`${alert.type}-${idx}`}
                        className={`flex gap-3 items-start rounded-lg border px-3 py-2 ${style.bg} ${style.border}`}
                      >
                        {style.icon}
                        <div className={`text-sm ${style.text}`}>
                          <p className="font-semibold">{alert.message}</p>
                          {alert.hint && <p className="text-xs mt-1 text-slate-600">{alert.hint}</p>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={`#logs-${run.run_number}`}
              onClick={(e) => e.stopPropagation()}
              className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Logs
            </a>
            <svg
              className={`w-6 h-6 text-slate-400 transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        
        {/* Progress Bar - only show for completed runs */}
        {(parsed.status === 'passed' || parsed.status === 'failed') && (
          <div className="mt-4">
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  isPassed 
                    ? 'bg-green-600' 
                    : 'bg-red-600'
                }`}
                style={{ width: `${passRate}%` }}
              ></div>
            </div>
          </div>
        )}
        {parsed.status === 'running' && (
          <div className="mt-4">
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full bg-yellow-600 animate-pulse"
                style={{ width: '50%' }}
              ></div>
            </div>
          </div>
        )}
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-6 bg-slate-50 border-t-2 border-slate-200 animate-fade-in">
          {/* Test Case Pass Rate */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <svg className="w-5 h-5 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h4 className="text-lg font-bold text-slate-900">Test Case Results</h4>
            </div>
            <TestCaseList testCases={parsed.test_cases} />
          </div>

          {/* Episodes - only show if we have structured episodes */}
          {parsed.episodes.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <svg className="w-5 h-5 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <h4 className="text-lg font-bold text-slate-900">Episodes ({parsed.episodes.length})</h4>
              </div>
              <div className="space-y-3">
                {parsed.episodes.map((episode, idx) => (
                  <EpisodeView key={idx} episode={episode} episodeNumber={idx} />
                ))}
              </div>
            </div>
          )}

          {/* Container Logs - always show when expanded */}
          <div id={`logs-${run.run_number}`} className="scroll-mt-8">
            <div className="flex items-center gap-2 mb-4">
              <svg className="w-5 h-5 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h4 className="text-lg font-bold text-slate-900">Container Logs</h4>
            </div>
            <LogViewer logs={run.logs || ''} />
          </div>
        </div>
      )}
    </div>
  );
}

