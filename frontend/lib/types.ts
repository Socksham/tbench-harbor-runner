export interface TestCase {
  name: string;
  status: 'passed' | 'failed';
  duration?: number;
}

export interface Episode {
  episode_number: number;
  commands?: string | null;
  explanation?: string | null;
  state_analysis?: string | null;
}

export interface RunAlert {
  type: 'info' | 'warning' | 'error';
  message: string;
  hint?: string;
}

export interface ParsedRunResult {
  run_number: number;
  status: 'passed' | 'failed' | 'running' | 'pending';
  tests_passed: number;
  tests_total: number;
  test_cases: TestCase[];
  episodes: Episode[];
  logs: string;
  alerts: RunAlert[];
}

