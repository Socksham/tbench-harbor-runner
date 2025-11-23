import TaskUpload from '@/components/TaskUpload';

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50 py-12 px-8">
      <div className="w-full max-w-7xl mx-auto">
        <div className="flex items-center gap-6 mb-8 animate-fade-in">
          <div className="flex-shrink-0 w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">
              Terminal-Bench Harbor Runner
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Upload and run Terminal-Bench tasks with Harbor harness
            </p>
          </div>
        </div>
        <div className="animate-fade-in" style={{ animationDelay: '0.1s' }}>
          <TaskUpload />
        </div>
      </div>
    </div>
  );
}
