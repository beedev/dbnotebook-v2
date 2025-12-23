import type {
  Notebook,
  NotebookListResponse,
  Document,
  DocumentListResponse,
  ModelsResponse,
  ChatRequest,
  UploadResponse,
  ImageGenerateRequest,
  ImageGenerateResponse,
  ApiError,
  WebSearchResponse,
  WebScrapePreviewResponse,
  WebSourceAddResponse,
  StudioGalleryResponse,
  StudioGenerateRequest,
  StudioGenerateResponse,
  StudioGeneratorsResponse,
  GeneratedContent,
} from '../types';

const API_BASE = '/api';

// Generic fetch wrapper with error handling
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  console.log(`[API] Fetching: ${url}`);

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    console.log(`[API] Response status: ${response.status} for ${url}`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`[API] Error response:`, errorData);
      const error: ApiError = {
        error: errorData.error || 'Unknown error',
        message: errorData.message || `HTTP ${response.status}`,
        status: response.status,
      };
      throw error;
    }

    const data = await response.json();
    console.log(`[API] Success response for ${url}:`, data);
    return data;
  } catch (err) {
    console.error(`[API] Fetch error for ${url}:`, err);
    throw err;
  }
}

// ============================================
// Notebook API
// ============================================

interface BackendNotebookListResponse {
  success: boolean;
  notebooks: Array<{
    id: string;
    name: string;
    description?: string;
    document_count?: number;
  }>;
  count: number;
}

interface BackendCreateNotebookResponse {
  success: boolean;
  notebook: { id: string; name: string };
  message: string;
}

export async function getNotebooks(): Promise<NotebookListResponse> {
  const response = await fetchApi<BackendNotebookListResponse>('/notebooks');
  return {
    notebooks: response.notebooks.map(n => ({
      id: n.id,
      name: n.name,
      description: n.description,
      documentCount: n.document_count || 0,
    })),
  };
}

export async function createNotebook(
  name: string,
  description?: string
): Promise<Notebook> {
  const response = await fetchApi<BackendCreateNotebookResponse>('/notebooks', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  });
  return {
    id: response.notebook.id,
    name: response.notebook.name,
    description: description,
    documentCount: 0,
  };
}

export async function getNotebook(id: string): Promise<Notebook> {
  const response = await fetchApi<{ success: boolean; notebook: { id: string; name: string; description?: string; document_count?: number } }>(`/notebooks/${id}`);
  return {
    id: response.notebook.id,
    name: response.notebook.name,
    description: response.notebook.description,
    documentCount: response.notebook.document_count || 0,
  };
}

export async function updateNotebook(
  id: string,
  data: Partial<Notebook>
): Promise<Notebook> {
  const response = await fetchApi<{ success: boolean; notebook: { id: string; name: string; description?: string } }>(`/notebooks/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  return {
    id: response.notebook.id,
    name: response.notebook.name,
    description: response.notebook.description,
    documentCount: 0,
  };
}

export async function deleteNotebook(id: string): Promise<void> {
  await fetchApi<{ success: boolean }>(`/notebooks/${id}`, {
    method: 'DELETE',
  });
}

// ============================================
// Document API
// ============================================

interface BackendDocumentListResponse {
  success: boolean;
  documents: Array<{
    source_id: string;
    file_name: string;  // Backend uses snake_case
    active?: boolean;
    file_type?: string;
    chunk_count?: number;
  }>;
  count: number;
}

export async function getDocuments(
  notebookId: string
): Promise<DocumentListResponse> {
  const response = await fetchApi<BackendDocumentListResponse>(`/notebooks/${notebookId}/documents`);
  return {
    documents: response.documents.map(d => ({
      source_id: d.source_id,
      filename: d.file_name,  // Map snake_case to camelCase
      active: d.active !== false, // default to true
      file_type: d.file_type,
      chunk_count: d.chunk_count,
    })),
  };
}

export async function uploadDocument(
  notebookId: string,
  file: File
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('files', file);  // Backend expects 'files' (plural)
  formData.append('notebook_id', notebookId);

  console.log(`[API] Uploading file: ${file.name} to notebook: ${notebookId}`);

  const response = await fetch(`/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Upload failed',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

export async function deleteDocument(
  notebookId: string,
  sourceId: string
): Promise<void> {
  await fetchApi<void>(`/notebooks/${notebookId}/documents/${sourceId}`, {
    method: 'DELETE',
  });
}

export async function toggleDocumentActive(
  notebookId: string,
  sourceId: string,
  active: boolean
): Promise<Document> {
  return fetchApi<Document>(`/notebooks/${notebookId}/documents/${sourceId}`, {
    method: 'PATCH',
    body: JSON.stringify({ active }),
  });
}

// ============================================
// Model API
// ============================================

interface BackendModel {
  name: string;
  display_name?: string;
  provider: string;
  type: string;
}

interface BackendModelsResponse {
  success: boolean;
  models: BackendModel[];
  count: number;
  default_model?: string;
  default_provider?: string;
}

export async function getModels(): Promise<ModelsResponse> {
  const response = await fetchApi<BackendModelsResponse>('/models');

  // Transform flat array to grouped format for frontend
  const grouped = new Map<string, BackendModel[]>();
  for (const model of response.models) {
    const provider = model.provider.toLowerCase();
    if (!grouped.has(provider)) {
      grouped.set(provider, []);
    }
    grouped.get(provider)!.push(model);
  }

  const models: ModelsResponse['models'] = [];
  for (const [provider, providerModels] of grouped) {
    models.push({
      provider: provider as 'ollama' | 'openai' | 'anthropic' | 'google',
      models: providerModels.map(m => ({
        name: m.name,
        displayName: m.display_name || m.name
      })),
    });
  }

  // Use default from config, or first available model
  const defaultModel = response.default_model || response.models[0]?.name || '';
  const defaultProvider = response.default_provider || response.models[0]?.provider.toLowerCase() || 'ollama';

  return {
    models,
    currentModel: defaultModel,
    currentProvider: defaultProvider as 'ollama' | 'openai' | 'anthropic' | 'google',
  };
}

export async function setModel(
  _model: string,
  _provider?: string
): Promise<{ success: boolean }> {
  // Model selection is handled client-side for now
  // The actual model is passed with each chat request
  return Promise.resolve({ success: true });
}

// ============================================
// Chat API with SSE Streaming
// ============================================

export interface SourceCitation {
  filename: string;
  page?: string | number;
  score?: number;
  snippet?: string;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onComplete: (fullResponse: string, sources?: SourceCitation[]) => void;
  onError: (error: string) => void;
  onImages?: (images: string[]) => void;
}

export async function sendChatMessage(
  request: ChatRequest,
  callbacks: StreamCallbacks
): Promise<void> {
  const response = await fetch('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      ...request,
      stream: true,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    callbacks.onError(errorData.message || `HTTP ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError('No response body');
    return;
  }

  const decoder = new TextDecoder();
  let fullResponse = '';
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            callbacks.onComplete(fullResponse);
            return;
          }

          try {
            const parsed = JSON.parse(data);

            if (parsed.token) {
              fullResponse += parsed.token;
              callbacks.onToken(parsed.token);
            }

            if (parsed.images && callbacks.onImages) {
              callbacks.onImages(parsed.images);
            }

            // Handle done signal with optional sources
            if (parsed.done) {
              const sources = parsed.sources || [];
              callbacks.onComplete(fullResponse, sources);
              return;
            }

            if (parsed.error) {
              callbacks.onError(parsed.error);
              return;
            }
          } catch {
            // Plain text token
            fullResponse += data;
            callbacks.onToken(data);
          }
        }
      }
    }

    // Handle any remaining buffer
    if (buffer.startsWith('data: ')) {
      const data = buffer.slice(6);
      if (data !== '[DONE]') {
        fullResponse += data;
        callbacks.onToken(data);
      }
    }

    callbacks.onComplete(fullResponse);
  } catch (error) {
    callbacks.onError(error instanceof Error ? error.message : 'Stream error');
  }
}

// Non-streaming chat (for simple requests)
export async function sendChatMessageSync(
  request: ChatRequest
): Promise<{ response: string; images?: string[] }> {
  const response = await fetch('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...request,
      stream: false,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Chat failed',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

// ============================================
// Image Generation API
// ============================================

export async function generateImage(
  request: ImageGenerateRequest
): Promise<ImageGenerateResponse> {
  const response = await fetch('/image/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Image generation failed',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

// ============================================
// Utility functions
// ============================================

export function clearChat(): Promise<{ success: boolean }> {
  return fetchApi<{ success: boolean }>('/chat/clear', {
    method: 'POST',
  });
}

export async function getSystemInfo(): Promise<{
  version: string;
  model: string;
  provider: string;
}> {
  return fetchApi('/info');
}

// ============================================
// Web Search API
// ============================================

export async function searchWeb(
  query: string,
  numResults: number = 5
): Promise<WebSearchResponse> {
  const response = await fetch('/api/web/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      num_results: numResults,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Web search failed',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

export async function previewWebUrl(
  url: string,
  maxChars: number = 500
): Promise<WebScrapePreviewResponse> {
  const response = await fetch('/api/web/scrape-preview', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      url,
      max_chars: maxChars,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Web preview failed',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

export async function addWebSources(
  notebookId: string,
  urls: string[],
  sourceName?: string
): Promise<WebSourceAddResponse> {
  const response = await fetch(`/api/notebooks/${notebookId}/web-sources`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      urls,
      source_name: sourceName,  // Pass search query for document naming
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Failed to add web sources',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

// ============================================
// Content Studio API
// ============================================

export async function getStudioGallery(options?: {
  type?: string;
  notebookId?: string;
  limit?: number;
  offset?: number;
}): Promise<StudioGalleryResponse> {
  const params = new URLSearchParams();
  if (options?.type) params.set('type', options.type);
  if (options?.notebookId) params.set('notebook_id', options.notebookId);
  if (options?.limit) params.set('limit', options.limit.toString());
  if (options?.offset) params.set('offset', options.offset.toString());

  const queryString = params.toString();
  const url = `/api/studio/gallery${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Failed to fetch gallery',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }
  return response.json();
}

export async function generateStudioContent(
  request: StudioGenerateRequest
): Promise<StudioGenerateResponse> {
  const response = await fetch('/api/studio/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Content generation failed',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

export async function getStudioContent(
  contentId: string
): Promise<{ success: boolean; content: GeneratedContent }> {
  const response = await fetch(`/api/studio/content/${contentId}`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Failed to fetch content',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

export async function deleteStudioContent(
  contentId: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`/api/studio/content/${contentId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Failed to delete content',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}

export async function getStudioGenerators(): Promise<StudioGeneratorsResponse> {
  const response = await fetch('/api/studio/generators');

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw {
      error: errorData.error || 'Failed to fetch generators',
      message: errorData.message || `HTTP ${response.status}`,
      status: response.status,
    };
  }

  return response.json();
}
