// Auth types

export interface User {
  user_id: string;
  username: string;
  email: string;
  roles: string[];
  api_key?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  user?: User;
  error?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// Admin types

export interface Role {
  role_id: string;
  name: string;
  description: string;
  permissions: string[];
  created_at?: string;
}

export interface UserWithRoles {
  user_id: string;
  username: string;
  email: string;
  roles: string[];
  api_key?: string;
  created_at?: string;
}

export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
  role?: string;
}

export interface NotebookAdmin {
  notebook_id: string;
  name: string;
  user_id: string;
  username: string;
  is_global: boolean;
  document_count: number;
  created_at?: string;
}

export interface AccessGrant {
  user_id: string;
  username: string;
  email?: string;
  access_level: 'owner' | 'editor' | 'viewer' | 'user';
  granted_at?: string;
}

// Token Metrics types

export interface TokenMetricsSummary {
  total_tokens: number;
  total_cost: number;
  total_queries: number;
  avg_response_time: number;
}

export interface ModelMetric {
  model: string;
  tokens: number;
  cost: number;
  queries: number;
}

export interface UserMetric {
  user_id: string;
  username: string;
  tokens: number;
  cost: number;
  queries: number;
}

export interface DayMetric {
  date: string;
  tokens: number;
  queries: number;
}

export interface TokenMetricsResponse {
  success: boolean;
  days: number;
  summary: TokenMetricsSummary;
  by_model: ModelMetric[];
  by_user: UserMetric[];
  by_day: DayMetric[];
}
