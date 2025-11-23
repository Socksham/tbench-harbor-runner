'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { listJobs, Job, JobStatus } from '@/lib/api';

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<JobStatus | 'all'>('all');

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 10000); // Refresh every 10 seconds
    
    return () => clearInterval(interval);
  }, []);

  const loadJobs = async () => {
    try {
      const data = await listJobs(100, 0);
      setJobs(data);
      setLoading(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
      setLoading(false);
    }
  };

  const filteredJobs = filter === 'all' 
    ? jobs 
    : jobs.filter(job => job.status === filter);

  const getStatusColor = (status: JobStatus) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'running':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: JobStatus) => {
    switch (status) {
      case 'completed':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
      case 'running':
        return (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const getTotalStats = () => {
    const total = jobs.length;
    const completed = jobs.filter(j => j.status === 'completed').length;
    const running = jobs.filter(j => 
      j.status === 'running' || j.runs.some(r => r.status === 'running')
    ).length;
    const failed = jobs.filter(j => j.status === 'failed').length;
    const pending = jobs.filter(j => 
      j.status === 'pending' && !j.runs.some(r => r.status === 'running')
    ).length;
    
    const totalRuns = jobs.reduce((sum, job) => sum + job.runs.length, 0);
    const completedRuns = jobs.reduce((sum, job) => 
      sum + job.runs.filter(r => r.status === 'completed').length
    , 0);
    const passedRuns = jobs.reduce((sum, job) => 
      sum + job.runs.filter(r => r.tests_passed && r.tests_total && r.tests_passed === r.tests_total).length
    , 0);

    return { total, completed, running, failed, pending, totalRuns, completedRuns, passedRuns };
  };

  const stats = getTotalStats();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading jobs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="container mx-auto px-4 max-w-7xl">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Jobs Dashboard</h1>
              <p className="text-sm text-slate-600 mt-1">
                Monitor all Terminal-Bench task executions
              </p>
            </div>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Upload New Tasks
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6">
            <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
              <div className="text-2xl font-bold text-slate-900">{stats.total}</div>
              <div className="text-xs text-slate-600 mt-1">Total Jobs</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4 border border-green-200">
              <div className="text-2xl font-bold text-green-700">{stats.completed}</div>
              <div className="text-xs text-green-600 mt-1">Completed</div>
            </div>
            <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
              <div className="text-2xl font-bold text-yellow-700">{stats.running}</div>
              <div className="text-xs text-yellow-600 mt-1">Running</div>
            </div>
            <div className="bg-red-50 rounded-lg p-4 border border-red-200">
              <div className="text-2xl font-bold text-red-700">{stats.failed}</div>
              <div className="text-xs text-red-600 mt-1">Failed</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="text-2xl font-bold text-gray-700">{stats.totalRuns}</div>
              <div className="text-xs text-gray-600 mt-1">Total Runs</div>
            </div>
          </div>

          {/* Filters */}
          <div className="mt-6 flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('pending')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === 'pending'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Pending
            </button>
            <button
              onClick={() => setFilter('running')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === 'running'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Running
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === 'completed'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Completed
            </button>
            <button
              onClick={() => setFilter('failed')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === 'failed'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Failed
            </button>
          </div>
        </div>

        {/* Jobs List */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700">
            {error}
          </div>
        )}

        {filteredJobs.length === 0 ? (
          <div className="bg-white rounded-lg shadow-lg p-12 text-center">
            <svg className="w-16 h-16 text-slate-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-slate-600 text-lg font-medium">No jobs found</p>
            <p className="text-slate-500 text-sm mt-2">
              {filter === 'all' 
                ? 'Upload your first task to get started'
                : `No jobs with status "${filter}"`}
            </p>
            {filter === 'all' && (
              <button
                onClick={() => router.push('/')}
                className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Upload Tasks
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredJobs.map((job) => {
              const completedRuns = job.runs.filter(r => r.status === 'completed').length;
              const passedRuns = job.runs.filter(r => 
                r.tests_passed && r.tests_total && r.tests_passed === r.tests_total
              ).length;
              const totalTests = job.runs.reduce((sum, r) => sum + (r.tests_passed || 0), 0);
              const totalTestCases = job.runs.reduce((sum, r) => sum + (r.tests_total || 0), 0);

              return (
                <div
                  key={job.id}
                  className="bg-white rounded-lg shadow-lg border border-slate-200 p-6 hover:shadow-xl transition-shadow cursor-pointer"
                  onClick={() => router.push(`/jobs/${job.id}`)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-slate-900">{job.task_name}</h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium border flex items-center gap-1 ${getStatusColor(job.status)}`}>
                          {getStatusIcon(job.status)}
                          {job.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-slate-600 mb-3">
                        <span>{job.harness}</span>
                        <span>•</span>
                        <span>{job.model}</span>
                        <span>•</span>
                        <span>{job.runs.length} runs</span>
                        {completedRuns > 0 && (
                          <>
                            <span>•</span>
                            <span className="text-green-600 font-medium">
                              {passedRuns}/{completedRuns} passed
                            </span>
                          </>
                        )}
                      </div>
                      {totalTestCases > 0 && (
                        <div className="text-sm text-slate-600">
                          <span className="font-medium">Test Results:</span>{' '}
                          <span className="text-green-600">{totalTests}</span>/{totalTestCases} tests passed
                        </div>
                      )}
                      <div className="text-xs text-slate-500 mt-2">
                        Created: {new Date(job.created_at).toLocaleString()}
                        {job.completed_at && (
                          <> • Completed: {new Date(job.completed_at).toLocaleString()}</>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/jobs/${job.id}`);
                      }}
                      className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
                    >
                      View Details →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

