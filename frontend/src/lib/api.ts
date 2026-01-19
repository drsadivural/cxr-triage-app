import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes for analysis
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      // Server responded with error
      const detail = (error.response.data as any)?.detail || error.message;
      console.error(`API Error ${error.response.status}: ${detail}`);
      error.message = detail;
    } else if (error.request) {
      // Request made but no response
      console.error('Network error: No response from server');
      error.message = 'Cannot connect to server. Please check if the backend is running.';
    }
    return Promise.reject(error);
  }
);

// Types
export interface Finding {
  finding_name: string;
  probability: number;
  calibrated_probability: number | null;
  status: 'NEG' | 'POSSIBLE' | 'POSITIVE' | 'UNCERTAIN';
  triage_threshold: number;
  strong_threshold: number;
}

export interface BoundingBox {
  finding_name: string;
  confidence: number;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  x_min_px?: number;
  y_min_px?: number;
  x_max_px?: number;
  y_max_px?: number;
}

export interface Report {
  findings_text: string;
  impression_text: string;
  llm_rewritten: boolean;
  disclaimer: string;
}

export interface AnalysisResult {
  study_id: string;
  status: string;
  triage_level: 'NORMAL' | 'ROUTINE' | 'URGENT' | null;
  triage_reasons: string[];
  findings: Finding[];
  bounding_boxes: BoundingBox[];
  report: Report | null;
  processing_time_ms: number | null;
  model_info: Record<string, any>;
  disclaimer: string;
}

export interface StudySummary {
  id: string;
  accession_number: string | null;
  patient_id: string | null;
  study_date: string | null;
  view_position: string | null;
  triage_level: string | null;
  status: string;
  created_at: string;
  processing_time_ms: number | null;
}

export interface WorklistResponse {
  studies: StudySummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface ModelInfo {
  name: string;
  type: string;
  version: string;
  status: string;
  findings_supported: string[];
}

export interface ModelsResponse {
  classifier: ModelInfo | null;
  detector: ModelInfo | null;
  models_available: boolean;
}

export interface Settings {
  database: {
    db_type: string;
    host: string;
    port: number;
    user: string;
    password: string;
    dbname: string;
    ssl_mode: string;
  };
  llm: {
    active_provider: string | null;
    llm_rewrite_enabled: boolean;
    azure_openai: {
      enabled: boolean;
      endpoint: string;
      deployment_name: string;
      api_version: string;
      api_key: string;
      temperature: number;
      top_p: number;
      max_tokens: number;
      streaming: boolean;
    };
    claude: {
      enabled: boolean;
      base_url: string;
      model: string;
      api_key: string;
      temperature: number;
      top_p: number;
      max_tokens: number;
    };
    gemini: {
      enabled: boolean;
      base_url: string;
      model: string;
      api_key: string;
      temperature: number;
      top_p: number;
      max_output_tokens: number;
    };
  };
  ai: {
    pneumothorax: { triage_threshold: number; strong_threshold: number; enabled: boolean };
    pleural_effusion: { triage_threshold: number; strong_threshold: number; enabled: boolean };
    consolidation: { triage_threshold: number; strong_threshold: number; enabled: boolean };
    cardiomegaly: { triage_threshold: number; strong_threshold: number; enabled: boolean };
    edema: { triage_threshold: number; strong_threshold: number; enabled: boolean };
    nodule: { triage_threshold: number; strong_threshold: number; enabled: boolean };
    mass: { triage_threshold: number; strong_threshold: number; enabled: boolean };
    detector_confidence: number;
    detector_iou: number;
    detector_max_boxes: number;
    calibration_enabled: boolean;
  };
}

export interface AuditLog {
  id: string;
  study_id: string | null;
  action: string;
  actor: string | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
}

export interface DashboardMetrics {
  latency: {
    avg_processing_time_ms: number;
    p50_processing_time_ms: number;
    p95_processing_time_ms: number;
    p99_processing_time_ms: number;
    total_studies: number;
    period_hours: number;
  };
  triage_distribution: {
    normal: number;
    routine: number;
    urgent: number;
    total: number;
  };
  studies_today: number;
  studies_this_week: number;
}

// API functions
export const apiClient = {
  // Health
  async getHealth() {
    const response = await api.get('/health');
    return response.data;
  },

  // Models
  async getModels(): Promise<ModelsResponse> {
    const response = await api.get('/v1/models');
    return response.data;
  },

  // Analysis
  async analyzeImage(file: File, asyncMode = false): Promise<{ study_id: string; status: string; result?: AnalysisResult }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('async_mode', String(asyncMode));

    const response = await api.post('/v1/cxr/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getResult(studyId: string): Promise<AnalysisResult> {
    const response = await api.get(`/v1/cxr/result/${studyId}`);
    return response.data;
  },

  // Worklist
  async getWorklist(page = 1, pageSize = 20, triageLevel?: string): Promise<WorklistResponse> {
    const params: Record<string, any> = { page, page_size: pageSize };
    if (triageLevel) params.triage_level = triageLevel;
    const response = await api.get('/v1/worklist', { params });
    return response.data;
  },

  async getStudy(studyId: string) {
    const response = await api.get(`/v1/study/${studyId}`);
    return response.data;
  },

  // Settings
  async getSettings(): Promise<Settings> {
    const response = await api.get('/v1/settings');
    return response.data;
  },

  async updateSettings(settings: Partial<Settings>): Promise<Settings> {
    const response = await api.put('/v1/settings', settings);
    return response.data;
  },

  async testConnection(config: any) {
    const response = await api.post('/v1/settings/test-connection', config);
    return response.data;
  },

  // Audit
  async getAuditLogs(page = 1, pageSize = 50, action?: string) {
    const params: Record<string, any> = { page, page_size: pageSize };
    if (action) params.action = action;
    const response = await api.get('/v1/audit', { params });
    return response.data;
  },

  // Metrics
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const response = await api.get('/v1/metrics/dashboard');
    return response.data;
  },

  // Export
  async exportStudy(studyId: string, format: 'json' | 'png' | 'dicom_sr') {
    const response = await api.get(`/v1/study/${studyId}/export/${format}`, {
      responseType: format === 'json' ? 'json' : 'blob',
    });
    return response.data;
  },

  // Images
  getImageUrl(studyId: string): string {
    return `${API_BASE_URL}/v1/study/${studyId}/image`;
  },

  getDicomUrl(studyId: string): string {
    return `${API_BASE_URL}/v1/study/${studyId}/dicom`;
  },

  // QA
  async createQAReview(review: {
    study_id: string;
    review_type: 'FP' | 'FN' | 'TP' | 'TN';
    finding_name?: string;
    reviewer?: string;
    notes?: string;
  }) {
    const response = await api.post('/v1/qa/review', review);
    return response.data;
  },
};

export default apiClient;
