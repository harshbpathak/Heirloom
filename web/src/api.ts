/**
 * Typed client for the Heirloom REST API.
 * Every shape mirrors the Pydantic schemas in core/models/schemas.py.
 */

export interface RepoStats {
  files?: number;
  loc?: number;
  decisions?: number;
  bus_factor_1_loc_pct?: number;
  at_risk_files?: number;
}

export interface RepoInfo {
  id: string;
  name: string;
  source: string;
  ingested_at: string | null;
  stats: RepoStats;
}

export interface TreeNode {
  name: string;
  type: 'dir' | 'file';
  path?: string;
  loc: number;
  bus_factor?: number | null;
  at_risk?: boolean;
  language?: string | null;
  children?: TreeNode[];
}

export interface EvidenceRef {
  type: string;
  ref: string;
  url: string | null;
}

export interface CompactDecision {
  id: string;
  title: string;
  reasoning: string;
  confidence: 'high' | 'medium' | 'low';
  date: string | null;
  evidence: EvidenceRef[];
  source?: string;
  summary?: string;
  alternatives?: string | null;
  files?: string[];
}

export interface Holder {
  name: string;
  ownership: number;
  last_active: string | null;
  inactive: boolean;
}

export interface ImpactItem {
  path: string;
  score: number;
  reason: string;
}

export interface WhyCard {
  path: string;
  language: string | null;
  loc: number;
  is_entry_point: boolean;
  summary: string;
  summary_source: 'llm' | 'comment' | 'none';
  decisions: CompactDecision[];
  holders: Holder[];
  bus_factor: number | null;
  at_risk: boolean;
  impact: ImpactItem[];
  warnings: { line: number; text: string }[];
  activity: { month: string; commits: number }[];
}

export interface TrailStep {
  path: string;
  reason: string;
  decisions: CompactDecision[];
  reading_minutes: number;
}

export interface Trail {
  topic: string | null;
  steps: TrailStep[];
}

export interface AskAnswer {
  answer: string;
  citations: string[];
  route: string;
}

export interface Person {
  name: string;
  owned_loc: number;
  files_over_40pct: number;
  last_active: string | null;
  inactive: boolean;
}

export interface RiskReport {
  at_risk_files: { path: string; loc: number; bus_factor: number | null }[];
  bus_factor_1_files: number;
  bus_factor_1_loc_pct: number;
  top_people: Person[];
}

export interface JobStatus {
  id: string;
  repo_id: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  progress: number;
  message: string;
}

export interface Health {
  ok: boolean;
  llm: string;
  demo: boolean;
}

/** Error envelope returned by the API. */
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  const body = await resp.json();
  if (!resp.ok) {
    const err = body?.error ?? { code: 'unknown', message: resp.statusText };
    throw new ApiError(err.code, err.message);
  }
  return body as T;
}

export const api = {
  health: () => request<Health>('/api/health'),
  repos: () => request<RepoInfo[]>('/api/repos'),
  ingest: (source: string) =>
    request<{ repo_id: string; job_id: string }>('/api/repos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source }),
    }),
  job: (id: string) => request<JobStatus>(`/api/jobs/${id}`),
  tree: (repo: string) => request<TreeNode>(`/api/repos/${repo}/tree`),
  why: (repo: string, path: string) =>
    request<WhyCard>(`/api/repos/${repo}/why?path=${encodeURIComponent(path)}`),
  whyAgent: (repo: string, path: string) =>
    request<Record<string, unknown>>(
      `/api/repos/${repo}/why?path=${encodeURIComponent(path)}&format=agent`,
    ),
  whyMarkdown: (repo: string, path: string) =>
    request<{ markdown: string }>(
      `/api/repos/${repo}/why?path=${encodeURIComponent(path)}&format=markdown`,
    ),
  trail: (repo: string, topic?: string) =>
    request<Trail>(`/api/repos/${repo}/trail${topic ? `?topic=${encodeURIComponent(topic)}` : ''}`),
  ask: (repo: string, question: string) =>
    request<AskAnswer>(`/api/repos/${repo}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),
  decisions: (repo: string, params: { q?: string; file?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.file) search.set('file', params.file);
    return request<{ total: number; items: CompactDecision[] }>(
      `/api/repos/${repo}/decisions?limit=500&${search}`,
    );
  },
  addDecision: (
    repo: string,
    body: { title: string; files: string[]; reasoning: string; alternatives?: string; author?: string },
  ) =>
    request<{ id: string; record_path: string | null }>(`/api/repos/${repo}/decisions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  risk: (repo: string) => request<RiskReport>(`/api/repos/${repo}/risk`),
  people: (repo: string) => request<Person[]>(`/api/repos/${repo}/people`),
};
