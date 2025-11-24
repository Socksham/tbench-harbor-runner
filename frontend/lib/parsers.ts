import { Run } from './api';
import { ParsedRunResult, TestCase, Episode, RunAlert } from './types';

/**
 * Parse Harbor result JSON to extract test cases
 */
export function parseTestCases(run: Run): TestCase[] {
  if (!run.result_path) {
    return [];
  }

  // Try to parse from logs or result_path
  // In a real implementation, you'd fetch the CTRF JSON from the backend
  // For now, we'll parse from the logs if they contain test information
  
  const testCases: TestCase[] = [];
  
  // If we have test counts, create placeholder test cases
  if (run.tests_total && run.tests_total > 0) {
    for (let i = 0; i < run.tests_total; i++) {
      testCases.push({
        name: `test_${i + 1}`,
        status: i < (run.tests_passed || 0) ? 'passed' : 'failed',
      });
    }
  }
  
  return testCases;
}

/**
 * Parse episodes from Harbor logs (legacy fallback)
 */
export function parseEpisodesFromLogs(logs: string | null): Episode[] {
  if (!logs) {
    return [];
  }

  const episodes: Episode[] = [];

  // Harbor logs typically contain episode information
  // This is a simplified parser - you may need to adjust based on actual Harbor log format
  const lines = logs.split('\n');
  let currentEpisode: Episode | null = null;
  let episodeNumber = 0;
  let foundEpisodeMarkers = false;

  for (const line of lines) {
    // Look for episode markers - be more specific to avoid false positives
    // Check for patterns like "Episode 1", "Episode:", "episode 0", etc.
    const episodeMatch = line.match(/Episode\s+\d+/i) ||
                        line.match(/^Episode\s*:/i) ||
                        (line.toLowerCase().includes('episode') && /^\s*Episode/i.test(line));

    if (episodeMatch) {
      foundEpisodeMarkers = true;
      if (currentEpisode) {
        episodes.push(currentEpisode);
      }
      episodeNumber++;
      currentEpisode = {
        episode_number: episodeNumber,
        commands: '',
      };
    } else if (currentEpisode) {
      // Accumulate commands and explanations
      if (line.trim().startsWith('$') || line.trim().startsWith('>')) {
        currentEpisode.commands = (currentEpisode.commands || '') + line + '\n';
      } else if (line.length > 50) {
        // Likely an explanation or state analysis
        if (!currentEpisode.explanation) {
          currentEpisode.explanation = line;
        } else if (!currentEpisode.state_analysis) {
          currentEpisode.state_analysis = line;
        }
      }
    }
  }

  if (currentEpisode) {
    episodes.push(currentEpisode);
  }

  // Only return episodes if we found actual episode markers
  // Otherwise return empty array (logs will be shown in Container Logs section only)
  return foundEpisodeMarkers ? episodes : [];
}

/**
 * Parse a Run into a ParsedRunResult
 */
function detectRunAlerts(run: Run): RunAlert[] {
  const alerts: RunAlert[] = [];
  const logBlob = `${run.error || ''}\n${run.logs || ''}`.toLowerCase();

  if (logBlob.includes('agenttimeouterror') || logBlob.includes('agent execution timed out')) {
    alerts.push({
      type: 'warning',
      message: 'Agent execution timed out while waiting for the LLM response.',
      hint: 'The OpenRouter call exceeded Harbor’s agent timeout (default 15 minutes). Consider reducing concurrent jobs or increasing the timeout.'
    });
  }

  if (logBlob.includes('unclosed connection')) {
    alerts.push({
      type: 'info',
      message: 'OpenAI/OpenRouter closed the HTTP connection before returning a response.',
      hint: 'Usually caused by a network hiccup or provider throttle. Harbor cancels the attempt once the connection drops.'
    });
  }

  if (logBlob.includes('openaiexception')) {
    alerts.push({
      type: 'error',
      message: 'OpenAI/OpenRouter reported an OpenAIException during completion.',
      hint: 'Check the logs for the provider’s error payload—this often points to quota exhaustion, invalid parameters, or a temporary upstream outage.'
    });
  }

  if (logBlob.includes('⚠️ note: harbor metrics computation failed'.toLowerCase())) {
    alerts.push({
      type: 'info',
      message: 'Harbor metrics post-processing failed, but the verifier results are still valid.',
      hint: 'This is a known Harbor bug when running uploaded tasks; no action is required unless you need the metrics table.'
    });
  }

  return alerts;
}

export function parseRunResult(run: Run): ParsedRunResult {
  const testCases = parseTestCases(run);

  // Use structured episodes from API if available, otherwise fall back to log parsing
  const episodes = run.episodes && run.episodes.length > 0
    ? run.episodes
    : parseEpisodesFromLogs(run.logs);

  // Determine status based on run status
  let status: 'passed' | 'failed' | 'running' | 'pending';
  if (run.status === 'pending') {
    status = 'pending';
  } else if (run.status === 'running') {
    status = 'running';
  } else if (run.status === 'completed') {
    status = (run.tests_passed || 0) > 0 ? 'passed' : 'failed';
  } else {
    // run.status === 'failed'
    status = 'failed';
  }

  return {
    run_number: run.run_number,
    status,
    tests_passed: run.tests_passed || 0,
    tests_total: run.tests_total || 0,
    test_cases: testCases,
    episodes: episodes,
    logs: run.logs || '',
    alerts: detectRunAlerts(run),
  };
}

