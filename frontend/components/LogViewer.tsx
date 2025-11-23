'use client';

import { useEffect, useRef, useState } from 'react';

interface LogViewerProps {
  logs: string;
  autoScroll?: boolean;
}

export default function LogViewer({ logs, autoScroll = true }: LogViewerProps) {
  const logRef = useRef<HTMLPreElement>(null);
  const [isAutoScrolling, setIsAutoScrolling] = useState(autoScroll);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isAutoScrolling && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs, isAutoScrolling]);

  const handleScroll = () => {
    if (logRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logRef.current;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
      setIsAutoScrolling(isAtBottom);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(logs || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="border-2 border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <div className="bg-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <h6 className="text-sm font-bold text-white">Container Logs</h6>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-slate-400 font-mono">{formatSize(logs.length)}</span>
          {isAutoScrolling && (
            <span className="text-xs text-emerald-400 flex items-center gap-1">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
              Auto-scroll
            </span>
          )}
          <button
            onClick={copyToClipboard}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-xs font-medium flex items-center gap-2"
            title="Copy logs to clipboard"
          >
            {copied ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied!
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>
      </div>
      <pre
        ref={logRef}
        onScroll={handleScroll}
        className="bg-slate-900 text-emerald-400 p-4 overflow-x-auto text-sm font-mono max-h-[600px] overflow-y-auto leading-relaxed"
      >
        {logs || (
          <span className="text-slate-500 italic">No logs available yet...</span>
        )}
      </pre>
    </div>
  );
}

