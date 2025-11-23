export interface TestCase {
  name: string;
  status: 'passed' | 'failed';
  duration?: number;
}

export interface Episode {
  episode_number: number;
  state_analysis?: string;
  explanation?: string;
  commands?: string;
  timestamp?: string;
}

export interface ParsedRunResult {
  run_number: number;
  status: 'passed' | 'failed' | 'running' | 'pending';
  tests_passed: number;
  tests_total: number;
  test_cases: TestCase[];
  episodes: Episode[];
  logs: string;
}

