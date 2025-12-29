import { useState, useCallback } from 'react';
import { searchWeb, previewWebUrl, addWebSources } from '../services/api';
import type { WebSearchResult, WebScrapePreviewResponse } from '../types';

export interface WebSearchState {
  query: string;
  results: WebSearchResult[];
  isSearching: boolean;
  isAdding: boolean;
  error: string | null;
  successMessage: string | null;
  selectedUrls: Set<string>;
  previewUrl: string | null;
  previewContent: WebScrapePreviewResponse | null;
  isLoadingPreview: boolean;
}

const initialState: WebSearchState = {
  query: '',
  results: [],
  isSearching: false,
  isAdding: false,
  error: null,
  successMessage: null,
  selectedUrls: new Set(),
  previewUrl: null,
  previewContent: null,
  isLoadingPreview: false,
};

export function useWebSearch() {
  const [state, setState] = useState<WebSearchState>(initialState);

  // Search the web
  const search = useCallback(async (searchQuery: string, numResults: number = 5) => {
    if (!searchQuery.trim()) return;

    setState((prev) => ({
      ...prev,
      isSearching: true,
      error: null,
      successMessage: null,
      results: [],
      selectedUrls: new Set(),
      query: searchQuery.trim(),
    }));

    try {
      const response = await searchWeb(searchQuery.trim(), numResults);
      setState((prev) => ({
        ...prev,
        results: response.results,
        isSearching: false,
        error: response.results.length === 0 ? 'No results found. Try a different search term.' : null,
      }));
    } catch (err) {
      console.error('Search error:', err);
      setState((prev) => ({
        ...prev,
        isSearching: false,
        error: err instanceof Error ? err.message : 'Search failed. Please try again.',
      }));
    }
  }, []);

  // Toggle URL selection
  const toggleUrl = useCallback((url: string) => {
    setState((prev) => {
      const newSelected = new Set(prev.selectedUrls);
      if (newSelected.has(url)) {
        newSelected.delete(url);
      } else {
        newSelected.add(url);
      }
      return { ...prev, selectedUrls: newSelected };
    });
  }, []);

  // Select all URLs
  const selectAll = useCallback(() => {
    setState((prev) => ({
      ...prev,
      selectedUrls: new Set(prev.results.map((r) => r.url)),
    }));
  }, []);

  // Clear all selections
  const selectNone = useCallback(() => {
    setState((prev) => ({
      ...prev,
      selectedUrls: new Set(),
    }));
  }, []);

  // Preview URL content
  const preview = useCallback(async (url: string, maxChars: number = 500) => {
    // Toggle off if clicking same URL
    if (state.previewUrl === url) {
      setState((prev) => ({
        ...prev,
        previewUrl: null,
        previewContent: null,
      }));
      return;
    }

    setState((prev) => ({
      ...prev,
      previewUrl: url,
      isLoadingPreview: true,
      previewContent: null,
    }));

    try {
      const previewData = await previewWebUrl(url, maxChars);
      setState((prev) => ({
        ...prev,
        previewContent: previewData,
        isLoadingPreview: false,
      }));
    } catch (err) {
      console.error('Preview error:', err);
      setState((prev) => ({
        ...prev,
        previewContent: null,
        isLoadingPreview: false,
      }));
    }
  }, [state.previewUrl]);

  // Import selected URLs to notebook
  const importSelected = useCallback(
    async (notebookId: string): Promise<{ success: boolean; message?: string }> => {
      if (!notebookId || state.selectedUrls.size === 0) {
        return { success: false, message: 'No notebook or URLs selected' };
      }

      setState((prev) => ({
        ...prev,
        isAdding: true,
        error: null,
        successMessage: null,
      }));

      try {
        const response = await addWebSources(
          notebookId,
          Array.from(state.selectedUrls),
          state.query // Pass search query as source name for document naming
        );

        setState((prev) => ({
          ...prev,
          isAdding: false,
          successMessage: `Added ${response.total_added} source(s) to notebook`,
          selectedUrls: new Set(),
          results: [],
          query: '',
        }));

        return { success: true, message: response.total_added.toString() };
      } catch (err) {
        console.error('Add sources error:', err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to add sources. Please try again.';
        setState((prev) => ({
          ...prev,
          isAdding: false,
          error: errorMessage,
        }));
        return { success: false, message: errorMessage };
      }
    },
    [state.selectedUrls, state.query]
  );

  // Clear all results and reset state
  const clearResults = useCallback(() => {
    setState(initialState);
  }, []);

  // Clear messages (error/success)
  const clearMessages = useCallback(() => {
    setState((prev) => ({
      ...prev,
      error: null,
      successMessage: null,
    }));
  }, []);

  return {
    // State
    query: state.query,
    results: state.results,
    isSearching: state.isSearching,
    isAdding: state.isAdding,
    error: state.error,
    successMessage: state.successMessage,
    selectedUrls: state.selectedUrls,
    previewUrl: state.previewUrl,
    previewContent: state.previewContent,
    isLoadingPreview: state.isLoadingPreview,

    // Actions
    search,
    toggleUrl,
    selectAll,
    selectNone,
    preview,
    importSelected,
    clearResults,
    clearMessages,
  };
}
