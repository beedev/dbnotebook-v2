import { useState, useEffect, useCallback } from 'react';
import type { ModelGroup, ModelProvider, ModelState } from '../types';
import * as api from '../services/api';

const initialState: ModelState = {
  models: [],
  selectedModel: '',
  selectedProvider: 'ollama',
  isLoading: false,
  error: null,
};

export function useModels() {
  const [state, setState] = useState<ModelState>(initialState);

  const fetchModels = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await api.getModels();
      setState({
        models: response.models,
        selectedModel: response.currentModel,
        selectedProvider: response.currentProvider,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to load models',
      }));
    }
  }, []);

  const selectModel = useCallback(
    async (model: string, provider?: ModelProvider) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        await api.setModel(model, provider);
        setState((prev) => ({
          ...prev,
          selectedModel: model,
          selectedProvider: provider || prev.selectedProvider,
          isLoading: false,
        }));
        return true;
      } catch (error) {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to set model',
        }));
        return false;
      }
    },
    []
  );

  const getModelsByProvider = useCallback(
    (provider: ModelProvider): ModelGroup | undefined => {
      return state.models.find((g) => g.provider === provider);
    },
    [state.models]
  );

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  return {
    ...state,
    fetchModels,
    selectModel,
    getModelsByProvider,
  };
}
