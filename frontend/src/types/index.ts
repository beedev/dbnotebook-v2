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
  // AI Transformation fields
  dense_summary?: string | null;
  key_insights?: string[] | null;
  transformation_status?: 'pending' | 'processing' | 'completed' | 'failed';
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

// Query settings for per-request tuning
export interface QuerySettings {
  search_style: number; // 0-100: 0 = keyword, 100 = semantic
  result_depth: 'focused' | 'balanced' | 'comprehensive';
  temperature: number; // 0-100: maps to 0-2.0
}

// Chat API types
export interface ChatRequest {
  message: string;
  notebook_id?: string;
  model?: string;
  stream?: boolean;
  query_settings?: QuerySettings;
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

// Web Search types
export interface WebSearchResult {
  url: string;
  title: string;
  description: string;
  score?: number;
}

export interface WebSearchResponse {
  success: boolean;
  results: WebSearchResult[];
  query: string;
}

export interface WebScrapePreviewResponse {
  success: boolean;
  url: string;
  title: string;
  content_preview: string;
  word_count: number;
}

export interface WebSourceAddRequest {
  urls: string[];
}

export interface WebSourceAdded {
  source_id: string;
  url: string;
  title: string;
  chunk_count: number;
  word_count?: number;
}

export interface WebSourceAddResponse {
  success: boolean;
  sources_added: WebSourceAdded[];
  total_added: number;
}

// Content Studio types
export interface GeneratedContent {
  content_id: string;
  content_type: 'infographic' | 'mindmap' | 'summary';
  title: string;
  thumbnail_url?: string;
  file_url?: string;
  source_notebook_id?: string;
  prompt_used?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface StudioGalleryResponse {
  success: boolean;
  items: GeneratedContent[];
  total: number;
}

export interface StudioGenerateRequest {
  notebook_id: string;
  type: 'infographic' | 'mindmap';
  prompt?: string;
  aspect_ratio?: string;
  reference_image?: string; // Base64 encoded image for brand extraction
}

export interface StudioGenerateResponse {
  success: boolean;
  content: GeneratedContent;
}

export interface StudioGeneratorInfo {
  content_type: string;
  name: string;
  available: boolean;
  supported_aspect_ratios?: string[];
  description?: string;
  output_format?: string;
}

export interface StudioGeneratorsResponse {
  success: boolean;
  generators: StudioGeneratorInfo[];
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

// Re-export SQL Chat types
export * from './sqlChat';
