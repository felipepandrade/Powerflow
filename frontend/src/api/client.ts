import axios from 'axios';

// Singleton HTTP Client configurado
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para anexar as chaves e provedor de LLM
apiClient.interceptors.request.use((config) => {
  const provider = localStorage.getItem('llm_provider');

  if (provider) {
    config.headers['x-llm-provider'] = provider;
  }

  return config;
});

// Tipos para as respostas (baseados no backend)
export interface HealthResponse {
  status: string;
  env?: string;
  version?: string;
}

// Funções de API
export const checkHealth = async (): Promise<HealthResponse> => {
  const response = await apiClient.get<HealthResponse>('/health/live');
  return response.data;
};

export type TaskStatus = 'inbox' | 'open' | 'in_progress' | 'waiting_on_others' | 'blocked' | 'done' | 'cancelled';
export type Priority = 'critical' | 'high' | 'medium' | 'low';

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: Priority;
  due_date: string | null;
  project_id?: string | null;
  waiting_on_id: string | null;
  last_activity_at: string | null;
}

export interface TaskTimelineItem {
  id: string;
  type: string;
  timestamp: string;
  from_status?: TaskStatus | null;
  to_status?: TaskStatus;
  actor?: string;
  content?: string;
  author?: string;
}

export interface TaskTimeline {
  task_id: string;
  title: string;
  status: TaskStatus;
  created_at: string;
  timeline: TaskTimelineItem[];
}

export interface TaskListResponse {
  data: Task[];
  count: number;
}

export interface TriagePayload {
  task_title?: string;
  task_description?: string;
  evidence_quote?: string;
  source_subject?: string;
  candidate_task_id?: string;
  candidate_task_title?: string;
  [key: string]: unknown;
}

export interface TriageItem {
  id: string;
  source_item_id: string;
  signal_type: string;
  state: string;
  payload: TriagePayload;
  decision_conf: number | null;
  created_at: string | null;
}

export interface TriageListResponse {
  data: TriageItem[];
  count: number;
}

export const getTasks = async (): Promise<TaskListResponse> => {
  const response = await apiClient.get<TaskListResponse>('/api/tasks');
  return response.data;
};

export const getTaskTimeline = async (taskId: string): Promise<TaskTimeline> => {
  const response = await apiClient.get<TaskTimeline>(`/api/tasks/${taskId}/timeline`);
  return response.data;
};

export const getTriageSignals = async (): Promise<TriageListResponse> => {
  const response = await apiClient.get<TriageListResponse>('/api/signals/triage');
  return response.data;
};

export const manageTask = async (taskId: string, payload: { status?: TaskStatus; title?: string; description?: string }) => {
  const response = await apiClient.patch<{ success: boolean; message: string }>(`/api/tasks/${taskId}`, payload);
  return response.data;
};

export const triageProposal = async (
  signalId: string,
  payload: { action: 'apply' | 'discard' | 'delegate'; task_id?: string; modifications?: Record<string, unknown> },
) => {
  const response = await apiClient.post<{ success: boolean; message: string }>(`/api/signals/${signalId}/triage`, payload);
  return response.data;
};

// --- Analytics & Org Types ---

export interface Coverage {
  level: 'high' | 'medium' | 'low' | 'unknown';
  pct: number | null;
  basis?: string | null;
}

export interface PeriodComparison {
  previous: number | null;
  delta_pct: number | null;
}

export interface MetricProvenance {
  source?: string | null;
  snapshot_dates?: string[];
  run_id?: string | null;
  evidence_count?: number | null;
}

export interface MetricValue {
  id: string;
  metric_id: string;
  metric_version?: number;
  name?: string;
  unit?: string;
  grain: string;
  period_start: string;
  period_end: string;
  dimension_key: string;
  dimension_value: string | null;
  value: number | null;
  numerator?: number | null;
  denominator?: number | null;
  formula?: string | null;
  coverage?: Coverage | null;
  is_suppressed: boolean;
  sample_size: number;
  suppression_reason?: string | null;
  caveat?: string | null;
  period_comparison?: PeriodComparison | null;
  provenance?: MetricProvenance | null;
  data_origin?: 'derived' | 'manual' | 'imported' | 'mixed';
  semantic_status?: 'good' | 'warning' | 'danger' | 'neutral';
  computed_at: string;
}

export interface MetricQuery {
  metric_id?: string;
  start_date?: string;
  end_date?: string;
  project_id?: string;
  area_id?: string;
  priority?: Priority;
}

export interface MetricEvidence {
  evidence_id: string;
  source_item_id: string;
  quote: string;
  role: string;
}

export interface TaskDrilldownItem {
  task_id: string;
  title: string | null;
  evidence: MetricEvidence[];
}

export interface CapacityDrilldownItem {
  source_item_id: string;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
}

export interface ProjectDrilldownItem {
  project_id: string;
  value: number | null;
  components: Record<string, number | null> | null;
}

export type MetricDrilldownItem = TaskDrilldownItem | CapacityDrilldownItem | ProjectDrilldownItem;

export interface MetricReconciliation {
  kind?: string;
  displayed_value?: number | null;
  drilldown_value?: number | null;
  reconciles: boolean;
}

export interface MetricDrilldownResponse {
  metric_id: string;
  formula: string;
  items: MetricDrilldownItem[];
  item_count: number;
  reconciliation: MetricReconciliation;
}

export interface Area {
  id: string;
  name: string;
  short_name?: string;
  kind: string;
  is_own_team: boolean;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  color?: string;
}

export interface DailyCapacity {
  snapshot_date: string;
  state: 'known' | 'unknown';
  meeting_minutes: number | null;
  meeting_count: number | null;
  available_minutes: number | null;
  utilization_pct: number | null;
  provenance: string;
}

export interface CalendarEventView {
  source_item_id: string;
  starts_at: string;
  ends_at: string;
  is_all_day: boolean;
  show_as: string | null;
  duration_minutes: number | null;
  is_redacted: boolean;
  subject: string | null;
  deep_link: string | null;
}

export interface CalendarCoverage {
  expected_days: number;
  covered_days: number;
  missing_dates: string[];
}

export interface CalendarRange {
  start_date: string;
  end_date: string;
  state: 'known' | 'unknown';
  coverage: CalendarCoverage;
  items: CalendarEventView[];
  item_count: number;
  provenance: string;
}
export interface InsightResult {
  insight_id: string;
  narrative_text: string;
  is_verified: boolean;
  discrepancies: number[];
}

// --- Analytics & Org Functions ---

export const getMetrics = async (params: MetricQuery = {}): Promise<MetricValue[]> => {
  const response = await apiClient.get<MetricValue[]>('/api/analytics/metrics', {
    params,
  });
  return response.data;
};

export const getMetricDrilldown = async (
  metricId: string,
  params: Pick<MetricQuery, 'start_date' | 'end_date' | 'project_id' | 'area_id' | 'priority'>,
): Promise<MetricDrilldownResponse> => {
  const response = await apiClient.get<MetricDrilldownResponse>(`/api/analytics/metrics/${encodeURIComponent(metricId)}/drilldown`, { params });
  return response.data;
};

export const computeMetrics = async (start_date?: string, end_date?: string): Promise<{ status: string; computed_metrics: number; data?: MetricValue[] }> => {
  const response = await apiClient.post<{ status: string; computed_metrics: number; data?: MetricValue[] }>('/api/analytics/compute', { start_date, end_date });
  return response.data;
};

export const buildSnapshots = async (snapshot_date?: string): Promise<{ status: string; result: Record<string, unknown> }> => {
  const response = await apiClient.post<{ status: string; result: Record<string, unknown> }>('/api/analytics/snapshots', undefined, { params: { snapshot_date } });
  return response.data;
};

export const generateInsight = async (scope = 'cockpit'): Promise<InsightResult> => {
  const response = await apiClient.post<{ status: string; insight: InsightResult }>('/api/analytics/insights', { scope });
  return response.data.insight;
};

export const getDailyCapacity = async (): Promise<DailyCapacity> => {
  const response = await apiClient.get<DailyCapacity>('/api/system/capacity');
  return response.data;
};

export const getCalendarEvents = async (startDate: string, endDate: string): Promise<CalendarRange> => {
  const response = await apiClient.get<CalendarRange>('/api/analytics/calendar', {
    params: { start_date: startDate, end_date: endDate },
  });
  return response.data;
};
export const getAreas = async (): Promise<Area[]> => {
  const response = await apiClient.get<Area[]>('/api/org/areas');
  return response.data;
};

export const getProjects = async (): Promise<Project[]> => {
  const response = await apiClient.get<Project[]>('/api/org/projects');
  return response.data;
};
