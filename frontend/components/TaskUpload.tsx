'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { uploadTasksBatch, HarnessType, ModelType, UploadResponse } from '@/lib/api';

export default function TaskUpload() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [harness, setHarness] = useState<HarnessType>('harbor');
  const [model, setModel] = useState<ModelType>('openai/gpt-4o');
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [nRuns, setNRuns] = useState(10);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [uploadResults, setUploadResults] = useState<UploadResponse[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const zipFiles = selectedFiles.filter(f => f.name.endsWith('.zip'));
    
    if (zipFiles.length !== selectedFiles.length) {
      setError('Only .zip files are allowed. Some files were ignored.');
    }
    
    setFiles(prev => [...prev, ...zipFiles]);
    setError(null);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }

    if (!openrouterKey.trim()) {
      setError('Please enter your OpenRouter API key');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress({});
    setUploadResults([]);

    try {
      const results = await uploadTasksBatch(files, harness, model, openrouterKey, nRuns);
      setUploadResults(results);
      setUploading(false);
      
      // Check if all uploads succeeded
      const failed = results.filter(r => r.status === 'failed');
      const succeeded = results.filter(r => r.status === 'queued' && r.job_id);
      
      if (failed.length > 0) {
        setError(`${failed.length} file(s) failed to upload. ${succeeded.length} job(s) created successfully.`);
      }
      
      // Scroll results into view
      setTimeout(() => {
        const resultsElement = document.getElementById('upload-results');
        if (resultsElement) {
          resultsElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 100);
      
      // Navigate to jobs dashboard after a longer delay to allow viewing results
      setTimeout(() => {
        router.push('/jobs');
      }, 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
      <div className="bg-blue-600 px-6 py-4 flex-shrink-0">
        <h2 className="text-xl font-bold text-white">Upload Terminal-Bench Task</h2>
        <p className="text-blue-100 text-xs mt-0.5">Configure your task and model settings</p>
      </div>
      
      <div className="p-6">
        {/* Success Banner */}
        {uploadResults.length > 0 && (
          <div className="mb-4 p-4 bg-green-50 border-2 border-green-200 rounded-lg">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-green-800 mb-1">
                  Upload Complete! {uploadResults.filter(r => r.status === 'queued').length} job(s) created successfully.
                </h4>
                <p className="text-xs text-green-700">
                  Redirecting to jobs dashboard in a few seconds... 
                  <button
                    onClick={() => router.push('/jobs')}
                    className="ml-2 text-green-800 font-medium underline hover:text-green-900"
                  >
                    Go now →
                  </button>
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-4">
            {/* File Upload */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Task ZIP Files {files.length > 0 && `(${files.length} selected)`}
              </label>
              <div className="relative">
                <input
                  type="file"
                  accept=".zip"
                  multiple
                  onChange={handleFileChange}
                  className="w-full px-3 py-2.5 border-2 border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-slate-50 hover:bg-white cursor-pointer file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 text-sm"
                />
              </div>
              {files.length > 0 && (
                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded-lg border border-slate-200">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <span className="text-xs text-slate-700 truncate flex-1">{file.name}</span>
                        <span className="text-xs text-slate-500 flex-shrink-0">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                      </div>
                      <button
                        onClick={() => removeFile(index)}
                        className="ml-2 p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors flex-shrink-0"
                        type="button"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <p className="mt-1 text-xs text-slate-500">You can select multiple ZIP files to upload and run concurrently</p>
            </div>

            {/* Harness Selection */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Harness
              </label>
              <select
                value={harness}
                onChange={(e) => setHarness(e.target.value as HarnessType)}
                className="w-full px-3 py-2.5 border-2 border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white hover:border-slate-300 text-sm text-slate-900"
              >
                <option value="harbor">Harbor (Terminal Bench 2)</option>
                <option value="terminus">Terminus (Terminal Bench 1)</option>
              </select>
            </div>

            {/* Model Selection */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value as ModelType)}
                className="w-full px-3 py-2.5 border-2 border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white hover:border-slate-300 text-sm text-slate-900"
              >
                <option value="openai/gpt-4o">GPT-4o</option>
                <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
                <option value="openai/gpt-5-mini">GPT-5 Mini</option>
                <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet</option>
                <option value="google/gemini-pro-1.5">Gemini Pro 1.5</option>
                <option value="meta-llama/llama-3.1-405b-instruct">Llama 3.1 405B</option>
              </select>
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-4">
            {/* API Key */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                OpenRouter API Key
              </label>
              <input
                type="text"
                value={openrouterKey}
                onChange={(e) => setOpenrouterKey(e.target.value)}
                placeholder="sk-or-v1-..."
                className="w-full px-3 py-2.5 border-2 border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white hover:border-slate-300 text-sm text-slate-900"
              />
              <p className="mt-1 text-xs text-slate-500">Your OpenRouter API key is used to authenticate with the OpenRouter API. You can get your API key from <a href="https://openrouter.ai/api-keys" target="_blank" className="text-blue-500 hover:text-blue-600">OpenRouter</a>.</p>
            </div>

            {/* Number of Runs */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Number of Runs
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={nRuns}
                onChange={(e) => setNRuns(parseInt(e.target.value) || 10)}
                className="w-full px-3 py-2.5 border-2 border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white hover:border-slate-300 text-sm text-slate-900"
              />
              <p className="mt-1 text-xs text-slate-500">Run the task multiple times to get statistical results</p>
            </div>
          </div>
        </div>

        {/* Upload Results */}
        {uploadResults.length > 0 && (
          <div id="upload-results" className="mt-4 space-y-2 max-h-64 overflow-y-auto">
            <h4 className="text-sm font-semibold text-slate-700 sticky top-0 bg-white pb-2 z-10">Upload Results:</h4>
            {uploadResults.map((result, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border-2 ${
                  result.status === 'queued'
                    ? 'bg-green-50 border-green-200 text-green-700'
                    : 'bg-red-50 border-red-200 text-red-700'
                }`}
              >
                <div className="flex items-start gap-2">
                  {result.status === 'queued' ? (
                    <svg className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  )}
                  <div className="flex-1">
                    <p className="text-xs font-medium">{result.message}</p>
                    {result.job_id && (
                      <button
                        onClick={() => router.push(`/jobs/${result.job_id}`)}
                        className="mt-1 text-xs text-blue-600 hover:text-blue-800 underline"
                      >
                        View Job →
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border-2 border-red-200 rounded-lg text-red-700 flex items-start gap-2 animate-slide-in">
            <svg className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-xs font-medium">{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <div className="mt-6">
          <button
            onClick={handleUpload}
            disabled={uploading || files.length === 0}
            className="w-full px-6 py-3.5 bg-blue-600 text-white rounded-lg font-semibold shadow-lg hover:shadow-xl hover:bg-blue-700 disabled:bg-slate-400 disabled:cursor-not-allowed disabled:shadow-none transform hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 flex items-center justify-center gap-2 text-sm"
          >
            {uploading ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Uploading {files.length} file(s) & Starting Jobs...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <span>
                  Upload {files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''}` : 'Files'} & Run 
                  {files.length > 0 && ` (${files.length * nRuns} total runs)`}
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

