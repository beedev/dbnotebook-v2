import { useState, useCallback } from 'react';
import { Upload, FileText, X, Loader2 } from 'lucide-react';

interface DocumentUploaderProps {
  onUpload: (file: File) => Promise<boolean>;
  disabled?: boolean;
}

export function DocumentUploader({ onUpload, disabled }: DocumentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setUploadQueue(prev => [...prev, ...files]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setUploadQueue(prev => [...prev, ...files]);
    }
    // Reset input
    e.target.value = '';
  }, []);

  const removeFromQueue = useCallback((index: number) => {
    setUploadQueue(prev => prev.filter((_, i) => i !== index));
  }, []);

  const uploadAll = useCallback(async () => {
    if (uploadQueue.length === 0) return;

    setIsUploading(true);
    const results: { file: File; success: boolean }[] = [];

    for (const file of uploadQueue) {
      const success = await onUpload(file);
      results.push({ file, success });
    }

    // Remove successful uploads from queue
    const failed = results.filter(r => !r.success).map(r => r.file);
    setUploadQueue(failed);
    setIsUploading(false);
  }, [uploadQueue, onUpload]);

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center
          transition-all duration-200
          ${isDragging
            ? 'border-primary bg-primary/5'
            : 'border-void-lighter hover:border-primary/50 hover:bg-void-surface/50'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        <input
          type="file"
          multiple
          onChange={handleFileSelect}
          disabled={disabled}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          accept=".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls"
        />

        <div className="flex flex-col items-center gap-3">
          <div className={`w-14 h-14 rounded-full flex items-center justify-center ${
            isDragging ? 'bg-primary/20' : 'bg-void-surface'
          }`}>
            <Upload className={`w-7 h-7 ${isDragging ? 'text-primary' : 'text-text-muted'}`} />
          </div>
          <div>
            <p className="text-text font-medium">
              {isDragging ? 'Drop files here' : 'Drag and drop files'}
            </p>
            <p className="text-sm text-text-muted mt-1">
              or click to browse
            </p>
          </div>
          <p className="text-xs text-text-muted">
            PDF, DOCX, TXT, MD, CSV, XLSX supported
          </p>
        </div>
      </div>

      {/* Upload queue */}
      {uploadQueue.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-text">
              {uploadQueue.length} file{uploadQueue.length > 1 ? 's' : ''} ready
            </span>
            <button
              onClick={uploadAll}
              disabled={isUploading}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload All
                </>
              )}
            </button>
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto">
            {uploadQueue.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center gap-3 p-3 bg-void-surface rounded-lg border border-void-lighter"
              >
                <FileText className="w-5 h-5 text-primary flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text truncate">{file.name}</p>
                  <p className="text-xs text-text-muted">
                    {formatFileSize(file.size)}
                  </p>
                </div>
                <button
                  onClick={() => removeFromQueue(index)}
                  disabled={isUploading}
                  className="p-1.5 rounded-lg text-text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
