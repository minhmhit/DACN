export interface BenchmarkRow {
  workload: string;
  variant: string;
  threads: number;
  total_throughput_ops: number;
  total_read_ops: number;
  total_write_ops: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  p999_ms: number;
  max_ms: number;
  variance_ms2: number;
}

export interface CboPlanComparison {
  parameter: string;
  opt: string;
  inv: string;
  none: string;
  ratio: string;
}

export interface PerfContextTelemetry {
  metric: string;
  k_opt: string;
  k_inv: string;
  ratio: string;
  impact: string;
}

export interface RulebookItem {
  id: number;
  title: string;
  target: string;
  statement: string;
  empiricalProof: string;
  riskIfViolated: string;
  checklist: string[];
  codeSnippet?: {
    language: string;
    title: string;
    code: string;
  };
}

export interface ComparisonDimension {
  dimension: string;
  traditional: string;
  aiDrl: string;
  ourRulebook: string;
}

export interface ChecklistItem {
  category: string;
  standard: string;
  risk: string;
  action: string;
}
