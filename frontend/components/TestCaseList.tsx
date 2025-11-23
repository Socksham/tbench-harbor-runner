'use client';

import { TestCase } from '@/lib/types';

interface TestCaseListProps {
  testCases: TestCase[];
}

export default function TestCaseList({ testCases }: TestCaseListProps) {
  if (testCases.length === 0) {
    return (
      <div className="text-sm text-slate-500 italic bg-slate-50 p-4 rounded-lg border-2 border-dashed border-slate-200">
        No test cases available
      </div>
    );
  }

  const passedCount = testCases.filter(tc => tc.status === 'passed').length;
  const totalCount = testCases.length;
  const passRate = totalCount > 0 ? (passedCount / totalCount) * 100 : 0;

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="bg-slate-50 p-4 rounded-xl border-2 border-slate-200">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-slate-700">Test Summary</span>
          <span className="text-sm font-bold text-slate-900">{passedCount}/{totalCount} passed</span>
        </div>
        <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-green-600 rounded-full transition-all duration-500"
            style={{ width: `${passRate}%` }}
          ></div>
        </div>
        <div className="text-xs text-slate-600 mt-2">{passRate.toFixed(1)}% success rate</div>
      </div>

      {/* Test Cases */}
      <div className="grid gap-2">
        {testCases.map((testCase, idx) => (
          <div
            key={idx}
            className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all duration-200 ${
              testCase.status === 'passed' 
                ? 'bg-green-50 border-green-200 hover:border-green-300 hover:shadow-md' 
                : 'bg-red-50 border-red-200 hover:border-red-300 hover:shadow-md'
            }`}
          >
            <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
              testCase.status === 'passed' 
                ? 'bg-green-100 text-green-700' 
                : 'bg-red-100 text-red-700'
            }`}>
              {testCase.status === 'passed' ? (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <span className={`text-sm font-mono font-semibold block truncate ${
                testCase.status === 'passed' ? 'text-green-900' : 'text-red-900'
              }`}>
                {testCase.name}
              </span>
            </div>
            <span className={`text-xs font-bold px-2 py-1 rounded-lg ${
              testCase.status === 'passed' 
                ? 'bg-green-200 text-green-800' 
                : 'bg-red-200 text-red-800'
            }`}>
              {testCase.status.toUpperCase()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

