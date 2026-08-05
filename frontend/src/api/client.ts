import axios from 'axios';

// Singleton HTTP Client configurado
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para anexar as chaves e provedor de LLM
apiClient.interceptors.request.use((config) => {
  const provider = localStorage.getItem('llm_provider');
  const apiKey = localStorage.getItem('llm_api_key');

  if (provider) {
    config.headers['x-llm-provider'] = provider;
  }
  if (apiKey) {
    config.headers['x-llm-api-key'] = apiKey;
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

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  due_date: string | null;
  waiting_on_id: string | null;
  last_activity_at: string | null;
}

export interface TaskListResponse {
  data: Task[];
  count: number;
}

export interface TriageItem {
  id: string;
  source_item_id: string;
  signal_type: string;
  state: string;
  payload: any;
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

export const getTriageSignals = async (): Promise<TriageListResponse> => {
  const response = await apiClient.get<TriageListResponse>('/api/signals/triage');
  return response.data;
};

export const manageTask = async (taskId: string, payload: { status?: string; title?: string; description?: string }) => {
  const response = await apiClient.patch(`/api/tasks/${taskId}`, payload);
  return response.data;
};

export const triageProposal = async (signalId: string, payload: { action: string; task_id?: string; modifications?: any }) => {
  const response = await apiClient.post(`/api/signals/${signalId}/triage`, payload);
  return response.data;
};
