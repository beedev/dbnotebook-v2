import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { Document } from '../types';

interface DocumentContextType {
  // State
  documents: Document[];
  isLoading: boolean;
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;

  // Actions
  setDocuments: (documents: Document[]) => void;
  addDocument: (document: Document) => void;
  removeDocument: (sourceId: string) => void;
  toggleDocument: (sourceId: string) => void;
  updateDocument: (sourceId: string, updates: Partial<Document>) => void;
  clearDocuments: () => void;
  setLoading: (loading: boolean) => void;
  setUploading: (uploading: boolean) => void;
  setUploadProgress: (progress: number) => void;
  clearError: () => void;
}

const DocumentContext = createContext<DocumentContextType | undefined>(undefined);

export function DocumentProvider({ children }: { children: ReactNode }) {
  const [documents, setDocumentsState] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgressState] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Set documents from external source
  const setDocuments = useCallback((newDocuments: Document[]) => {
    setDocumentsState(newDocuments);
    setError(null);
  }, []);

  // Add a new document (optimistic update)
  const addDocument = useCallback((document: Document) => {
    setDocumentsState((prev) => {
      // Prevent duplicates
      const exists = prev.some((doc) => doc.source_id === document.source_id);
      if (exists) {
        return prev;
      }
      return [...prev, document];
    });
    setError(null);
  }, []);

  // Remove a document by source_id
  const removeDocument = useCallback((sourceId: string) => {
    setDocumentsState((prev) => prev.filter((doc) => doc.source_id !== sourceId));
    setError(null);
  }, []);

  // Toggle document active status (for RAG inclusion)
  const toggleDocument = useCallback((sourceId: string) => {
    setDocumentsState((prev) =>
      prev.map((doc) =>
        doc.source_id === sourceId
          ? { ...doc, active: !doc.active }
          : doc
      )
    );
    setError(null);
  }, []);

  // Update a document with partial changes
  const updateDocument = useCallback((sourceId: string, updates: Partial<Document>) => {
    setDocumentsState((prev) =>
      prev.map((doc) =>
        doc.source_id === sourceId
          ? { ...doc, ...updates }
          : doc
      )
    );
    setError(null);
  }, []);

  // Clear all documents
  const clearDocuments = useCallback(() => {
    setDocumentsState([]);
    setError(null);
  }, []);

  // Control loading state
  const setLoading = useCallback((loading: boolean) => {
    setIsLoading(loading);
    if (loading) {
      setError(null);
    }
  }, []);

  // Control uploading state
  const setUploading = useCallback((uploading: boolean) => {
    setIsUploading(uploading);
    if (!uploading) {
      setUploadProgressState(0);
    }
    if (uploading) {
      setError(null);
    }
  }, []);

  // Update upload progress (0-100)
  const setUploadProgress = useCallback((progress: number) => {
    setUploadProgressState(Math.min(100, Math.max(0, progress)));
  }, []);

  // Clear error state
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: DocumentContextType = {
    documents,
    isLoading,
    isUploading,
    uploadProgress,
    error,
    setDocuments,
    addDocument,
    removeDocument,
    toggleDocument,
    updateDocument,
    clearDocuments,
    setLoading,
    setUploading,
    setUploadProgress,
    clearError,
  };

  return (
    <DocumentContext.Provider value={value}>
      {children}
    </DocumentContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDocument() {
  const context = useContext(DocumentContext);

  if (!context) {
    throw new Error('useDocument must be used within DocumentProvider');
  }

  return context;
}
