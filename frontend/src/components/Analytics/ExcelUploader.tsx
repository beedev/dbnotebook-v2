/**
 * Excel File Uploader Component
 *
 * Provides drag-and-drop file upload for Excel/CSV files
 * with validation and progress feedback.
 * Shows requirements modal after file selection for optional customization.
 */

import { useCallback, useState } from 'react';
import { Upload, FileSpreadsheet, X, AlertCircle } from 'lucide-react';
import { useAnalytics } from '../../contexts/AnalyticsContext';
import { RequirementsModal } from './RequirementsModal';

const ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

interface ExcelUploaderProps {
  onUploadComplete?: (sessionId: string) => void;
  notebookId?: string;
  className?: string;
}

export function ExcelUploader({
  onUploadComplete,
  notebookId,
  className = '',
}: ExcelUploaderProps) {
  const { runFullAnalysis, analysisState, analysisProgress, error, resetDashboard } = useAnalytics();
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showRequirementsModal, setShowRequirementsModal] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const validateFile = useCallback((file: File): string | null => {
    // Check extension
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
    }

    // Check size
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size: ${MAX_FILE_SIZE / (1024 * 1024)}MB`;
    }

    return null;
  }, []);

  const handleFile = useCallback(async (file: File) => {
    setValidationError(null);

    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      return;
    }

    // Store file and show requirements modal
    setPendingFile(file);
    setShowRequirementsModal(true);
  }, [validateFile]);

  // Handle requirements submission - analyze with user requirements
  const handleRequirementsSubmit = useCallback(async (requirements: string) => {
    if (!pendingFile) return;

    setShowRequirementsModal(false);
    setSelectedFile(pendingFile);
    setPendingFile(null);

    // Start the full analysis pipeline with requirements
    const success = await runFullAnalysis(pendingFile, notebookId, requirements);

    if (success && onUploadComplete) {
      // Get session ID from context - it will be set after upload
    }
  }, [pendingFile, runFullAnalysis, notebookId, onUploadComplete]);

  // Handle skip - analyze without requirements
  const handleRequirementsSkip = useCallback(async () => {
    if (!pendingFile) return;

    setShowRequirementsModal(false);
    setSelectedFile(pendingFile);
    setPendingFile(null);

    // Start the full analysis pipeline without requirements
    const success = await runFullAnalysis(pendingFile, notebookId);

    if (success && onUploadComplete) {
      // Get session ID from context - it will be set after upload
    }
  }, [pendingFile, runFullAnalysis, notebookId, onUploadComplete]);

  // Handle modal close - cancel the upload
  const handleRequirementsClose = useCallback(() => {
    setShowRequirementsModal(false);
    setPendingFile(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  }, [handleFile]);

  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setValidationError(null);
    resetDashboard();
  }, [resetDashboard]);

  const isUploading = analysisState === 'uploading' || analysisState === 'parsing' || analysisState === 'profiling' || analysisState === 'analyzing';
  const isError = analysisState === 'error';
  const isComplete = analysisState === 'complete';

  // Show progress view when uploading
  if (isUploading && selectedFile) {
    return (
      <div className={`analytics-uploader analytics-uploader--uploading ${className}`}>
        <div className="analytics-uploader__progress-container">
          <FileSpreadsheet className="analytics-uploader__file-icon" size={48} />
          <div className="analytics-uploader__progress-info">
            <p className="analytics-uploader__filename">{selectedFile.name}</p>
            <p className="analytics-uploader__status">
              {analysisState === 'uploading' && 'Uploading...'}
              {analysisState === 'parsing' && 'Parsing data...'}
              {analysisState === 'profiling' && 'Generating profile...'}
              {analysisState === 'analyzing' && 'Creating dashboard...'}
            </p>
            <div className="analytics-uploader__progress-bar">
              <div
                className="analytics-uploader__progress-fill"
                style={{ width: `${analysisProgress}%` }}
              />
            </div>
            <p className="analytics-uploader__progress-text">{analysisProgress}%</p>
          </div>
        </div>
      </div>
    );
  }

  // Show success view when complete
  if (isComplete && selectedFile) {
    return (
      <div className={`analytics-uploader analytics-uploader--complete ${className}`}>
        <div className="analytics-uploader__success-container">
          <FileSpreadsheet className="analytics-uploader__file-icon analytics-uploader__file-icon--success" size={48} />
          <div className="analytics-uploader__success-info">
            <p className="analytics-uploader__filename">{selectedFile.name}</p>
            <p className="analytics-uploader__success-text">Analysis complete!</p>
          </div>
          <button
            onClick={handleReset}
            className="analytics-uploader__reset-btn"
            title="Upload a different file"
          >
            <X size={20} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`analytics-uploader ${className}`}>
      <div
        className={`analytics-uploader__dropzone ${isDragOver ? 'analytics-uploader__dropzone--active' : ''} ${isError ? 'analytics-uploader__dropzone--error' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          type="file"
          accept={ALLOWED_EXTENSIONS.join(',')}
          onChange={handleFileSelect}
          className="analytics-uploader__input"
          id="excel-upload-input"
        />
        <label htmlFor="excel-upload-input" className="analytics-uploader__label">
          <div className="analytics-uploader__icon-container">
            <Upload className="analytics-uploader__upload-icon" size={32} />
          </div>
          <div className="analytics-uploader__text">
            <p className="analytics-uploader__title">
              {isDragOver ? 'Drop your file here' : 'Upload Excel or CSV file'}
            </p>
            <p className="analytics-uploader__subtitle">
              Drag and drop or click to browse
            </p>
            <p className="analytics-uploader__formats">
              Supports: {ALLOWED_EXTENSIONS.join(', ')} (max {MAX_FILE_SIZE / (1024 * 1024)}MB)
            </p>
          </div>
        </label>
      </div>

      {(validationError || error) && (
        <div className="analytics-uploader__error">
          <AlertCircle size={16} />
          <span>{validationError || error}</span>
        </div>
      )}

      {/* Requirements Modal - shown after file selection */}
      <RequirementsModal
        isOpen={showRequirementsModal}
        fileName={pendingFile?.name || ''}
        onSubmit={handleRequirementsSubmit}
        onSkip={handleRequirementsSkip}
        onClose={handleRequirementsClose}
      />
    </div>
  );
}

export default ExcelUploader;
