'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getJob, Job, Run } from '@/lib/api';
import AttemptCard from '@/components/AttemptCard';

export default function JobPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;
  
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRuns, setExpandedRuns] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadJob();
    const interval = setInterval(loadJob, 5000); // Refresh every 5 seconds
    
    return () => clearInterval(interval);
  }, [jobId]);

  const loadJob = async () => {
    try {
      const data = await getJob(jobId);
      setJob(data);
      setLoading(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load job');
      setLoading(false);
    }
  };

  const toggleRun = (runNumber: number) => {
    setExpandedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(runNumber)) {
        next.delete(runNumber);
      } else {
        next.add(runNumber);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-blue-200 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
          </div>
          <p className="text-slate-600 font-medium">Loading job details...</p>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div className="text-center bg-white rounded-2xl shadow-xl p-8 max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <p className="text-red-600 font-semibold mb-2 text-lg">{error || 'Job not found'}</p>
          <p className="text-slate-600 text-sm mb-6">The job you're looking for doesn't exist or couldn't be loaded.</p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  const statusConfig = {
    completed: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300', icon: '✓' },
    running: { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300', icon: '⟳' },
    failed: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300', icon: '✕' },
    pending: { bg: 'bg-slate-100', text: 'text-slate-800', border: 'border-slate-300', icon: '○' },
  };

  const status = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.pending;

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8 mb-8 animate-fade-in">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-slate-900">{job.task_name}</h1>
                  <p className="text-sm text-slate-600 mt-1">
                    <span className="font-mono text-xs">{job.id}</span> • {job.harness} • {job.model}
                  </p>
                </div>
              </div>
            </div>
            <button
              onClick={loadJob}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 shadow-lg hover:shadow-xl transition-all transform hover:scale-105 flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>
          
          <div className="flex flex-wrap items-center gap-4">
            <span className={`px-4 py-2 rounded-xl text-sm font-semibold border-2 ${status.bg} ${status.text} ${status.border} flex items-center gap-2`}>
              <span className="text-lg">{status.icon}</span>
              {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
            </span>
            <div className="flex items-center gap-2 text-slate-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
              <span className="font-medium">{job.runs.length} {job.runs.length === 1 ? 'run' : 'runs'}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-600">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{new Date(job.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Attempt Cards */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-6">
            <h2 className="text-2xl font-bold text-slate-900">LLM Attempt Results</h2>
            <div className="flex-1 h-px bg-slate-300"></div>
            <span className="text-sm text-slate-500 font-medium">{job.runs.length} {job.runs.length === 1 ? 'attempt' : 'attempts'}</span>
          </div>
          <div className="space-y-4">
            {job.runs.map((run, idx) => (
              <div key={run.id} id={`run-${run.run_number}`} className="animate-fade-in" style={{ animationDelay: `${idx * 0.05}s` }}>
                <AttemptCard
                  run={run}
                  isExpanded={expandedRuns.has(run.run_number)}
                  onToggle={() => {
                    toggleRun(run.run_number);
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Back Button */}
        <div className="text-center">
          <button
            onClick={() => router.push('/')}
            className="px-8 py-3 bg-white text-slate-700 rounded-xl font-semibold hover:bg-slate-50 shadow-lg hover:shadow-xl transition-all transform hover:scale-105 border-2 border-slate-200 flex items-center gap-2 mx-auto"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Upload New Task
          </button>
        </div>
      </div>
    </div>
  );
}

