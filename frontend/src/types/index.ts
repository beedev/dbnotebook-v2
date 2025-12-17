// Source citation type
export interface SourceCitation {
  filename: string;
  page?: string | number;
  score?: number;
  snippet?: string;
}

// Chat types
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  images?: string[]; // Generated image paths
  sources?: SourceCitation[]; // Document sources/citations
}

export interface ChatSession {
  id: string;
  notebookId: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

// Notebook types
export interface Notebook {
  id: string;
  name: string;
  description?: string;
  documentCount?: number;
  createdAt?: Date;
  updatedAt?: Date;
}

export interface NotebookListResponse {
  notebooks: Notebook[];
}

// Document types
export interface Document {
  source_id: string;
  filename: string;
  file_type?: string;
  chunk_count?: number;
  uploadedAt?: Date;
  active?: boolean;
}

export interface DocumentListResponse {
  documents: Document[];
}

// Model types
export type ModelProvider = 'ollama' | 'openai' | 'anthropic' | 'google';

export interface Model {
  name: string;
  displayName?: string;
}

export interface ModelGroup {
  provider: ModelProvider;
  models: Model[];
}

export interface ModelsResponse {
  models: ModelGroup[];
  currentModel: string;
  currentProvider: ModelProvider;
}

// Chat API types
export interface ChatRequest {
  message: string;
  notebook_id?: string;
  model?: string;
  stream?: boolean;
}

export interface ChatResponse {
  response: string;
  sources?: DocumentSource[];
  images?: string[];
}

export interface DocumentSource {
  filename: string;
  chunk_id: string;
  relevance_score: number;
}

// Upload types
export interface UploadResponse {
  success: boolean;
  message: string;
  filename?: string;
  source_id?: string;
}

// Image generation types
export interface ImageGenerateRequest {
  prompt: string;
  num_images?: number;
  aspect_ratio?: string;
}

export interface ImageGenerateResponse {
  success: boolean;
  images: string[];
  prompt: string;
}

// Toast notification types
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

// API Error type
export interface ApiError {
  error: string;
  message: string;
  status: number;
}

// State types for hooks
export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
}

export interface NotebookState {
  notebooks: Notebook[];
  selectedNotebook: Notebook | null;
  isLoading: boolean;
  error: string | null;
}

export interface ModelState {
  models: ModelGroup[];
  selectedModel: string;
  selectedProvider: ModelProvider;
  isLoading: boolean;
  error: string | null;
}
