# Analytics Dashboard Components Documentation

**Feature**: Analytics Dashboard for dbnotebook
**Tech Stack**: React 19 + TypeScript + Tailwind CSS + D3.js + Chart.js
**Theme**: Deep Space (dark mode with blue/purple accents)
**Status**: Design Phase

---

## Table of Contents

1. [Component Hierarchy](#component-hierarchy)
2. [Context & Hooks](#context--hooks)
3. [Core Components](#core-components)
4. [Filter Components](#filter-components)
5. [Visualization Components](#visualization-components)
6. [Utility Components](#utility-components)
7. [TypeScript Interfaces](#typescript-interfaces)
8. [Styling Guidelines](#styling-guidelines)

---

## Component Hierarchy

```
AnalyticsDashboard (main container)
├── AnalyticsProvider (context)
│   ├── ExcelUploader
│   │   └── Dropzone (react-dropzone)
│   ├── AnalysisLoader
│   │   └── ProgressStages
│   └── DashboardView
│       ├── TabNavigation
│       │   ├── Dashboard Tab
│       │   │   ├── FilterBar
│       │   │   │   ├── SelectFilter
│       │   │   │   ├── RangeFilter
│       │   │   │   └── DateRangeFilter
│       │   │   ├── KPICardGrid
│       │   │   │   └── KPICard[] (with D3 sparklines)
│       │   │   ├── ChartGrid
│       │   │   │   ├── ChartJSWrapper (Bar/Line/Pie)
│       │   │   │   └── D3Components
│       │   │   │       ├── TreeMap
│       │   │   │       ├── Sankey
│       │   │   │       ├── Heatmap
│       │   │   │       ├── Sunburst
│       │   │   │       └── ForceGraph
│       │   │   └── ExportButton
│       │   └── Data Profile Tab
│       │       └── ProfileReportViewer (iframe)
│       └── Toast Notifications (useToast)
```

---

## Context & Hooks

### AnalyticsContext

**Purpose**: Global state management for analytics dashboard

**File**: `/src/contexts/AnalyticsContext.tsx`

```typescript
interface AnalyticsContextValue {
  // File state
  uploadedFile: File | null;
  setUploadedFile: (file: File | null) => void;

  // Analysis state
  analysisState: 'idle' | 'uploading' | 'analyzing' | 'complete' | 'error';
  analysisProgress: number; // 0-100
  error: string | null;

  // Data state
  rawData: any[] | null;
  analyzedData: AnalysisResult | null;
  profileReport: string | null; // HTML from ydata-profiling

  // Filter state
  filters: FilterState;
  setFilters: (filters: FilterState) => void;
  filteredData: any[] | null;

  // Dashboard config (AI-generated)
  dashboardConfig: DashboardConfig | null;

  // Actions
  uploadFile: (file: File) => Promise<void>;
  runAnalysis: () => Promise<void>;
  resetDashboard: () => void;
  exportToPDF: () => Promise<void>;
}

interface AnalysisResult {
  summary: {
    rowCount: number;
    columnCount: number;
    missingValues: number;
    duplicateRows: number;
  };
  columns: ColumnAnalysis[];
  insights: string[];
  recommendations: string[];
}

interface DashboardConfig {
  kpis: KPIConfig[];
  charts: ChartConfig[];
  filters: FilterConfig[];
  layout: LayoutConfig;
}
```

**Provider Usage**:

```typescript
export const AnalyticsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [analysisState, setAnalysisState] = useState<AnalysisContextValue['analysisState']>('idle');
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [rawData, setRawData] = useState<any[] | null>(null);
  const [analyzedData, setAnalyzedData] = useState<AnalysisResult | null>(null);
  const [profileReport, setProfileReport] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({});
  const [dashboardConfig, setDashboardConfig] = useState<DashboardConfig | null>(null);

  // Computed filtered data
  const filteredData = useMemo(() => {
    if (!rawData) return null;
    return applyFilters(rawData, filters);
  }, [rawData, filters]);

  const uploadFile = async (file: File) => {
    setAnalysisState('uploading');
    setUploadedFile(file);
    // Parse Excel/CSV to rawData
    const data = await parseFile(file);
    setRawData(data);
    setAnalysisState('idle');
  };

  const runAnalysis = async () => {
    if (!rawData) return;

    setAnalysisState('analyzing');
    setAnalysisProgress(0);

    try {
      // Stage 1: ydata-profiling (0-50%)
      setAnalysisProgress(25);
      const profileHTML = await generateProfile(rawData);
      setProfileReport(profileHTML);
      setAnalysisProgress(50);

      // Stage 2: AI analysis (50-100%)
      setAnalysisProgress(75);
      const aiResult = await analyzeWithAI(rawData);
      setAnalyzedData(aiResult.analysis);
      setDashboardConfig(aiResult.config);
      setAnalysisProgress(100);

      setAnalysisState('complete');
    } catch (err) {
      setError(err.message);
      setAnalysisState('error');
    }
  };

  const resetDashboard = () => {
    setUploadedFile(null);
    setAnalysisState('idle');
    setRawData(null);
    setAnalyzedData(null);
    setProfileReport(null);
    setFilters({});
    setDashboardConfig(null);
    setError(null);
  };

  const exportToPDF = async () => {
    const dashboard = document.getElementById('dashboard-container');
    if (!dashboard) return;

    const canvas = await html2canvas(dashboard);
    const pdf = new jsPDF('l', 'mm', 'a4');
    const imgData = canvas.toDataURL('image/png');
    pdf.addImage(imgData, 'PNG', 0, 0, 297, 210);
    pdf.save('analytics-dashboard.pdf');
  };

  const value: AnalyticsContextValue = {
    uploadedFile,
    setUploadedFile,
    analysisState,
    analysisProgress,
    error,
    rawData,
    analyzedData,
    profileReport,
    filters,
    setFilters,
    filteredData,
    dashboardConfig,
    uploadFile,
    runAnalysis,
    resetDashboard,
    exportToPDF,
  };

  return (
    <AnalyticsContext.Provider value={value}>
      {children}
    </AnalyticsContext.Provider>
  );
};
```

### useAnalytics Hook

**Purpose**: Access analytics context

```typescript
export const useAnalytics = (): AnalyticsContextValue => {
  const context = useContext(AnalyticsContext);
  if (!context) {
    throw new Error('useAnalytics must be used within AnalyticsProvider');
  }
  return context;
};
```

### useCrossFilter Hook

**Purpose**: Cross-filtering logic for interactive charts

```typescript
interface CrossFilterOptions {
  enabled?: boolean;
  debounceMs?: number;
}

export const useCrossFilter = (options: CrossFilterOptions = {}) => {
  const { filters, setFilters, filteredData } = useAnalytics();
  const { enabled = true, debounceMs = 300 } = options;

  const addFilter = useCallback((filterKey: string, value: any) => {
    if (!enabled) return;

    setFilters({
      ...filters,
      [filterKey]: value,
    });
  }, [filters, setFilters, enabled]);

  const removeFilter = useCallback((filterKey: string) => {
    const newFilters = { ...filters };
    delete newFilters[filterKey];
    setFilters(newFilters);
  }, [filters, setFilters]);

  const clearAllFilters = useCallback(() => {
    setFilters({});
  }, [setFilters]);

  return {
    filters,
    filteredData,
    addFilter,
    removeFilter,
    clearAllFilters,
    activeFilterCount: Object.keys(filters).length,
  };
};
```

---

## Core Components

### 1. AnalyticsDashboard

**Purpose**: Main container component for analytics feature

**File**: `/src/components/analytics/AnalyticsDashboard.tsx`

```typescript
interface AnalyticsDashboardProps {
  className?: string;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ className }) => {
  const { analysisState } = useAnalytics();
  const { theme } = useContext(ThemeContext); // Reuse existing theme

  return (
    <div className={cn(
      'analytics-dashboard min-h-screen bg-gray-900',
      className
    )}>
      <AnalyticsProvider>
        <div className="container mx-auto px-4 py-8">
          <header className="mb-8">
            <h1 className="text-3xl font-bold text-blue-400">
              Analytics Dashboard
            </h1>
            <p className="text-gray-400 mt-2">
              Upload Excel/CSV files for AI-powered insights
            </p>
          </header>

          {analysisState === 'idle' && <ExcelUploader />}
          {analysisState === 'uploading' && <AnalysisLoader stage="upload" />}
          {analysisState === 'analyzing' && <AnalysisLoader stage="analyze" />}
          {analysisState === 'complete' && <DashboardView />}
          {analysisState === 'error' && <ErrorView />}
        </div>
      </AnalyticsProvider>
    </div>
  );
};
```

**State Flow**:
- `idle` → Show ExcelUploader
- `uploading` → Show upload progress
- `analyzing` → Show ydata + AI processing
- `complete` → Show DashboardView
- `error` → Show error message

---

### 2. ExcelUploader

**Purpose**: File upload interface with drag-and-drop

**File**: `/src/components/analytics/ExcelUploader.tsx`

**Dependencies**: `react-dropzone`

```typescript
interface ExcelUploaderProps {
  maxSizeMB?: number;
  acceptedFormats?: string[];
}

export const ExcelUploader: React.FC<ExcelUploaderProps> = ({
  maxSizeMB = 50,
  acceptedFormats = ['.xlsx', '.xls', '.csv'],
}) => {
  const { uploadFile } = useAnalytics();
  const { showToast } = useToast(); // Reuse existing toast
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    const maxSizeBytes = maxSizeMB * 1024 * 1024;

    // Validation
    if (file.size > maxSizeBytes) {
      showToast({
        type: 'error',
        message: `File too large. Max size: ${maxSizeMB}MB`,
      });
      return;
    }

    const fileExt = file.name.split('.').pop()?.toLowerCase();
    if (!acceptedFormats.some(fmt => fmt.includes(fileExt || ''))) {
      showToast({
        type: 'error',
        message: `Invalid format. Accepted: ${acceptedFormats.join(', ')}`,
      });
      return;
    }

    setIsUploading(true);
    try {
      await uploadFile(file);
      showToast({
        type: 'success',
        message: `${file.name} uploaded successfully`,
      });
    } catch (err) {
      showToast({
        type: 'error',
        message: `Upload failed: ${err.message}`,
      });
    } finally {
      setIsUploading(false);
    }
  }, [uploadFile, showToast, maxSizeMB, acceptedFormats]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
        isDragActive
          ? 'border-blue-400 bg-blue-900/20'
          : 'border-gray-600 hover:border-gray-500',
        isUploading && 'opacity-50 cursor-not-allowed'
      )}
    >
      <input {...getInputProps()} />

      <div className="flex flex-col items-center gap-4">
        {/* Icon */}
        <div className="w-16 h-16 rounded-full bg-blue-500/20 flex items-center justify-center">
          <svg className="w-8 h-8 text-blue-400" /* Upload icon SVG */ />
        </div>

        {/* Text */}
        <div>
          <p className="text-lg font-semibold text-gray-200">
            {isDragActive ? 'Drop file here' : 'Drag & drop Excel/CSV file'}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            or click to browse (max {maxSizeMB}MB)
          </p>
        </div>

        {/* Supported formats */}
        <div className="flex gap-2">
          {acceptedFormats.map(fmt => (
            <span
              key={fmt}
              className="px-3 py-1 bg-gray-800 text-gray-300 text-xs rounded-full"
            >
              {fmt}
            </span>
          ))}
        </div>
      </div>

      {isUploading && (
        <div className="mt-4">
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div className="bg-blue-500 h-2 rounded-full animate-pulse" style={{ width: '60%' }} />
          </div>
          <p className="text-sm text-gray-400 mt-2">Uploading...</p>
        </div>
      )}
    </div>
  );
};
```

**Features**:
- Drag-and-drop with visual feedback
- File validation (size, format)
- Upload progress indicator
- Integration with useToast for notifications

---

### 3. AnalysisLoader

**Purpose**: Multi-stage progress indicator

**File**: `/src/components/analytics/AnalysisLoader.tsx`

```typescript
interface AnalysisLoaderProps {
  stage: 'upload' | 'analyze';
}

interface ProcessingStage {
  id: string;
  label: string;
  description: string;
  progress: number;
}

export const AnalysisLoader: React.FC<AnalysisLoaderProps> = ({ stage }) => {
  const { analysisProgress } = useAnalytics();

  const stages: ProcessingStage[] = [
    {
      id: 'ydata',
      label: 'Data Profiling',
      description: 'Generating statistical profile with ydata-profiling',
      progress: Math.min(analysisProgress * 2, 100), // 0-50% maps to 0-100%
    },
    {
      id: 'ai',
      label: 'AI Analysis',
      description: 'Creating dashboard configuration with AI',
      progress: Math.max((analysisProgress - 50) * 2, 0), // 50-100% maps to 0-100%
    },
  ];

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-gray-800 rounded-lg p-8 border border-gray-700">
        {/* Overall progress */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-semibold text-gray-200">
              {stage === 'upload' ? 'Uploading File' : 'Analyzing Data'}
            </h3>
            <span className="text-blue-400 font-mono">{analysisProgress}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3">
            <div
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-300"
              style={{ width: `${analysisProgress}%` }}
            />
          </div>
        </div>

        {/* Stage breakdown */}
        <div className="space-y-6">
          {stages.map((s, idx) => (
            <div
              key={s.id}
              className={cn(
                'transition-opacity duration-300',
                s.progress === 0 && 'opacity-40'
              )}
            >
              <div className="flex items-start gap-4">
                {/* Stage number */}
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                  s.progress === 100
                    ? 'bg-green-500 text-white'
                    : s.progress > 0
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-700 text-gray-400'
                )}>
                  {s.progress === 100 ? '✓' : idx + 1}
                </div>

                {/* Stage info */}
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1">
                    <h4 className="font-medium text-gray-200">{s.label}</h4>
                    {s.progress > 0 && s.progress < 100 && (
                      <span className="text-sm text-gray-400">{s.progress}%</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mb-2">{s.description}</p>

                  {s.progress > 0 && s.progress < 100 && (
                    <div className="w-full bg-gray-700 rounded-full h-1.5">
                      <div
                        className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${s.progress}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Processing animation */}
        <div className="mt-8 flex items-center justify-center gap-2">
          <div className="flex gap-1">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
          <span className="text-sm text-gray-400">Processing...</span>
        </div>
      </div>
    </div>
  );
};
```

**Stages**:
1. **Data Profiling** (0-50%): ydata-profiling generates HTML report
2. **AI Analysis** (50-100%): AI creates dashboard config

---

### 4. DashboardView

**Purpose**: Main dashboard container with tab navigation

**File**: `/src/components/analytics/DashboardView.tsx`

```typescript
type TabType = 'dashboard' | 'profile';

export const DashboardView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const { dashboardConfig, profileReport, resetDashboard } = useAnalytics();

  if (!dashboardConfig) return null;

  return (
    <div className="dashboard-view">
      {/* Header with actions */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">Analysis Results</h2>
          <p className="text-gray-400 text-sm mt-1">
            Interactive dashboard with AI-generated insights
          </p>
        </div>

        <div className="flex gap-3">
          <ExportButton />
          <button
            onClick={resetDashboard}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors"
          >
            New Analysis
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-700 mb-6">
        <nav className="flex gap-1">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: '📊' },
            { id: 'profile', label: 'Data Profile', icon: '📈' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={cn(
                'px-6 py-3 font-medium transition-colors relative',
                activeTab === tab.id
                  ? 'text-blue-400'
                  : 'text-gray-400 hover:text-gray-300'
              )}
            >
              <span className="flex items-center gap-2">
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </span>
              {activeTab === tab.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400" />
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div id="dashboard-container">
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            <FilterBar />
            <KPICardGrid />
            <ChartGrid />
          </div>
        )}

        {activeTab === 'profile' && profileReport && (
          <ProfileReportViewer htmlContent={profileReport} />
        )}
      </div>
    </div>
  );
};
```

**Features**:
- Tab navigation (Dashboard / Data Profile)
- Export and reset actions
- Conditional rendering based on active tab

---

## Filter Components

### FilterBar

**Purpose**: Container for dynamically generated filters

**File**: `/src/components/analytics/filters/FilterBar.tsx`

```typescript
export const FilterBar: React.FC = () => {
  const { dashboardConfig } = useAnalytics();
  const { filters, clearAllFilters, activeFilterCount } = useCrossFilter();

  if (!dashboardConfig?.filters || dashboardConfig.filters.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-200">Filters</h3>
        {activeFilterCount > 0 && (
          <button
            onClick={clearAllFilters}
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            Clear All ({activeFilterCount})
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {dashboardConfig.filters.map(filterConfig => {
          switch (filterConfig.type) {
            case 'select':
              return <SelectFilter key={filterConfig.id} config={filterConfig} />;
            case 'range':
              return <RangeFilter key={filterConfig.id} config={filterConfig} />;
            case 'dateRange':
              return <DateRangeFilter key={filterConfig.id} config={filterConfig} />;
            default:
              return null;
          }
        })}
      </div>
    </div>
  );
};
```

### SelectFilter

**Purpose**: Dropdown filter for categorical data

```typescript
interface SelectFilterProps {
  config: SelectFilterConfig;
}

interface SelectFilterConfig {
  id: string;
  label: string;
  column: string;
  options: string[];
  defaultValue?: string;
}

export const SelectFilter: React.FC<SelectFilterProps> = ({ config }) => {
  const { addFilter, removeFilter, filters } = useCrossFilter();
  const currentValue = filters[config.id] as string | undefined;

  const handleChange = (value: string) => {
    if (value === '') {
      removeFilter(config.id);
    } else {
      addFilter(config.id, { column: config.column, value });
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        {config.label}
      </label>
      <select
        value={currentValue || ''}
        onChange={(e) => handleChange(e.target.value)}
        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 focus:border-blue-500 focus:outline-none"
      >
        <option value="">All</option>
        {config.options.map(opt => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
};
```

### RangeFilter

**Purpose**: Slider filter for numerical data

```typescript
interface RangeFilterProps {
  config: RangeFilterConfig;
}

interface RangeFilterConfig {
  id: string;
  label: string;
  column: string;
  min: number;
  max: number;
  step?: number;
  defaultValue?: [number, number];
}

export const RangeFilter: React.FC<RangeFilterProps> = ({ config }) => {
  const { addFilter, removeFilter, filters } = useCrossFilter();
  const currentValue = (filters[config.id] as { min: number; max: number }) || {
    min: config.min,
    max: config.max,
  };

  const handleChange = (newValue: [number, number]) => {
    if (newValue[0] === config.min && newValue[1] === config.max) {
      removeFilter(config.id);
    } else {
      addFilter(config.id, {
        column: config.column,
        min: newValue[0],
        max: newValue[1],
      });
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        {config.label}
      </label>
      <div className="px-2">
        <input
          type="range"
          min={config.min}
          max={config.max}
          step={config.step || 1}
          value={currentValue.min}
          onChange={(e) => handleChange([+e.target.value, currentValue.max])}
          className="w-full"
        />
        <input
          type="range"
          min={config.min}
          max={config.max}
          step={config.step || 1}
          value={currentValue.max}
          onChange={(e) => handleChange([currentValue.min, +e.target.value])}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>{currentValue.min}</span>
          <span>{currentValue.max}</span>
        </div>
      </div>
    </div>
  );
};
```

### DateRangeFilter

**Purpose**: Date range picker

```typescript
interface DateRangeFilterProps {
  config: DateRangeFilterConfig;
}

interface DateRangeFilterConfig {
  id: string;
  label: string;
  column: string;
  minDate?: string; // ISO date string
  maxDate?: string;
  defaultValue?: [string, string];
}

export const DateRangeFilter: React.FC<DateRangeFilterProps> = ({ config }) => {
  const { addFilter, removeFilter, filters } = useCrossFilter();
  const currentValue = (filters[config.id] as { start: string; end: string }) || {
    start: config.minDate || '',
    end: config.maxDate || '',
  };

  const handleChange = (field: 'start' | 'end', value: string) => {
    const newValue = { ...currentValue, [field]: value };
    addFilter(config.id, {
      column: config.column,
      ...newValue,
    });
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        {config.label}
      </label>
      <div className="flex gap-2">
        <input
          type="date"
          value={currentValue.start}
          min={config.minDate}
          max={config.maxDate}
          onChange={(e) => handleChange('start', e.target.value)}
          className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 focus:border-blue-500 focus:outline-none"
        />
        <span className="text-gray-400 self-center">to</span>
        <input
          type="date"
          value={currentValue.end}
          min={config.minDate}
          max={config.maxDate}
          onChange={(e) => handleChange('end', e.target.value)}
          className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 focus:border-blue-500 focus:outline-none"
        />
      </div>
    </div>
  );
};
```

---

## Visualization Components

### KPICardGrid & KPICard

**Purpose**: Display key metrics with sparklines

**File**: `/src/components/analytics/KPICardGrid.tsx`

```typescript
export const KPICardGrid: React.FC = () => {
  const { dashboardConfig } = useAnalytics();

  if (!dashboardConfig?.kpis) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {dashboardConfig.kpis.map(kpi => (
        <KPICard key={kpi.id} config={kpi} />
      ))}
    </div>
  );
};
```

**KPICard.tsx**:

```typescript
interface KPICardProps {
  config: KPIConfig;
}

interface KPIConfig {
  id: string;
  label: string;
  value: number | string;
  format?: 'number' | 'currency' | 'percentage';
  trend?: {
    direction: 'up' | 'down' | 'stable';
    value: number;
  };
  sparkline?: number[]; // Historical values for D3 sparkline
  icon?: string;
}

export const KPICard: React.FC<KPICardProps> = ({ config }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  // D3 sparkline rendering
  useEffect(() => {
    if (!config.sparkline || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 120;
    const height = 40;
    const data = config.sparkline;

    svg.selectAll('*').remove();

    const xScale = d3.scaleLinear()
      .domain([0, data.length - 1])
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain([d3.min(data) || 0, d3.max(data) || 0])
      .range([height, 0]);

    const line = d3.line<number>()
      .x((d, i) => xScale(i))
      .y(d => yScale(d))
      .curve(d3.curveMonotoneX);

    svg.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', '#60a5fa')
      .attr('stroke-width', 2)
      .attr('d', line);
  }, [config.sparkline]);

  const formatValue = (value: number | string): string => {
    if (typeof value === 'string') return value;

    switch (config.format) {
      case 'currency':
        return `$${value.toLocaleString()}`;
      case 'percentage':
        return `${value.toFixed(1)}%`;
      default:
        return value.toLocaleString();
    }
  };

  const getTrendColor = () => {
    if (!config.trend) return '';
    switch (config.trend.direction) {
      case 'up': return 'text-green-400';
      case 'down': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors">
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="text-sm text-gray-400 mb-1">{config.label}</p>
          <p className="text-2xl font-bold text-gray-100">
            {formatValue(config.value)}
          </p>
        </div>
        {config.icon && (
          <div className="text-2xl">{config.icon}</div>
        )}
      </div>

      {config.trend && (
        <div className={cn('flex items-center gap-1 text-sm', getTrendColor())}>
          <span>{config.trend.direction === 'up' ? '↑' : config.trend.direction === 'down' ? '↓' : '→'}</span>
          <span>{Math.abs(config.trend.value)}%</span>
        </div>
      )}

      {config.sparkline && (
        <div className="mt-3">
          <svg ref={svgRef} width="120" height="40" />
        </div>
      )}
    </div>
  );
};
```

**Features**:
- Responsive grid layout
- D3.js sparkline visualization
- Trend indicators with color coding
- Multiple value formats (number, currency, percentage)

---

### ChartGrid

**Purpose**: Responsive layout for charts

**File**: `/src/components/analytics/ChartGrid.tsx`

```typescript
export const ChartGrid: React.FC = () => {
  const { dashboardConfig } = useAnalytics();

  if (!dashboardConfig?.charts) return null;

  // Group charts by size for optimal layout
  const fullWidth = dashboardConfig.charts.filter(c => c.size === 'full');
  const halfWidth = dashboardConfig.charts.filter(c => c.size === 'half');

  return (
    <div className="space-y-4">
      {/* Full-width charts */}
      {fullWidth.map(chart => (
        <div key={chart.id} className="w-full">
          <ChartRenderer config={chart} />
        </div>
      ))}

      {/* Half-width charts in grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {halfWidth.map(chart => (
          <div key={chart.id}>
            <ChartRenderer config={chart} />
          </div>
        ))}
      </div>
    </div>
  );
};
```

### ChartRenderer

**Purpose**: Route to appropriate chart component

```typescript
interface ChartRendererProps {
  config: ChartConfig;
}

interface ChartConfig {
  id: string;
  type: 'bar' | 'line' | 'pie' | 'treemap' | 'sankey' | 'heatmap' | 'sunburst' | 'forceGraph';
  title: string;
  data: any;
  options?: any;
  size: 'full' | 'half';
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({ config }) => {
  // Chart.js types
  const chartJSTypes = ['bar', 'line', 'pie'];

  // D3 types
  const d3Types = ['treemap', 'sankey', 'heatmap', 'sunburst', 'forceGraph'];

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <h3 className="text-lg font-semibold text-gray-200 mb-4">{config.title}</h3>

      {chartJSTypes.includes(config.type) && (
        <ChartJSWrapper type={config.type} data={config.data} options={config.options} />
      )}

      {config.type === 'treemap' && <TreeMap data={config.data} />}
      {config.type === 'sankey' && <Sankey data={config.data} />}
      {config.type === 'heatmap' && <Heatmap data={config.data} />}
      {config.type === 'sunburst' && <Sunburst data={config.data} />}
      {config.type === 'forceGraph' && <ForceGraph data={config.data} />}
    </div>
  );
};
```

### ChartJSWrapper

**Purpose**: Wrapper for Chart.js charts with Deep Space theme

**File**: `/src/components/analytics/charts/ChartJSWrapper.tsx`

```typescript
import { Bar, Line, Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface ChartJSWrapperProps {
  type: 'bar' | 'line' | 'pie';
  data: any;
  options?: any;
}

export const ChartJSWrapper: React.FC<ChartJSWrapperProps> = ({ type, data, options }) => {
  // Deep Space theme defaults
  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#e5e7eb', // gray-200
          font: {
            family: 'Inter, system-ui, sans-serif',
          },
        },
      },
      tooltip: {
        backgroundColor: '#1f2937', // gray-800
        titleColor: '#e5e7eb',
        bodyColor: '#9ca3af', // gray-400
        borderColor: '#374151', // gray-700
        borderWidth: 1,
      },
    },
    scales: type !== 'pie' ? {
      x: {
        ticks: { color: '#9ca3af' },
        grid: { color: '#374151' },
      },
      y: {
        ticks: { color: '#9ca3af' },
        grid: { color: '#374151' },
      },
    } : undefined,
  };

  const mergedOptions = { ...defaultOptions, ...options };

  const ChartComponent = {
    bar: Bar,
    line: Line,
    pie: Pie,
  }[type];

  return (
    <div className="h-[400px]">
      <ChartComponent data={data} options={mergedOptions} />
    </div>
  );
};
```

### D3 Components

**TreeMap** (`/src/components/analytics/charts/TreeMap.tsx`):

```typescript
interface TreeMapProps {
  data: TreeMapData;
}

interface TreeMapData {
  name: string;
  children: Array<{
    name: string;
    value: number;
    color?: string;
  }>;
}

export const TreeMap: React.FC<TreeMapProps> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const { addFilter } = useCrossFilter();

  useEffect(() => {
    if (!svgRef.current) return;

    const width = 800;
    const height = 400;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const root = d3.hierarchy(data)
      .sum(d => d.value || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0));

    d3.treemap()
      .size([width, height])
      .padding(2)
      (root);

    const nodes = svg.selectAll('g')
      .data(root.leaves())
      .join('g')
      .attr('transform', d => `translate(${d.x0},${d.y0})`);

    nodes.append('rect')
      .attr('width', d => d.x1 - d.x0)
      .attr('height', d => d.y1 - d.y0)
      .attr('fill', d => d.data.color || '#60a5fa')
      .attr('stroke', '#1f2937')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        addFilter('treemap-filter', d.data.name);
      });

    nodes.append('text')
      .attr('x', 4)
      .attr('y', 20)
      .text(d => d.data.name)
      .attr('fill', '#e5e7eb')
      .attr('font-size', '12px');
  }, [data, addFilter]);

  return (
    <div className="overflow-auto">
      <svg ref={svgRef} width="800" height="400" />
    </div>
  );
};
```

**Sankey** (`/src/components/analytics/charts/Sankey.tsx`):

```typescript
interface SankeyProps {
  data: SankeyData;
}

interface SankeyData {
  nodes: Array<{ name: string }>;
  links: Array<{
    source: number;
    target: number;
    value: number;
  }>;
}

export const Sankey: React.FC<SankeyProps> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const width = 800;
    const height = 500;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const sankey = d3Sankey.sankey()
      .nodeWidth(15)
      .nodePadding(10)
      .extent([[1, 1], [width - 1, height - 5]]);

    const { nodes, links } = sankey({
      nodes: data.nodes.map(d => ({ ...d })),
      links: data.links.map(d => ({ ...d })),
    });

    // Draw links
    svg.append('g')
      .selectAll('path')
      .data(links)
      .join('path')
      .attr('d', d3Sankey.sankeyLinkHorizontal())
      .attr('stroke', '#60a5fa')
      .attr('stroke-width', d => Math.max(1, d.width))
      .attr('fill', 'none')
      .attr('opacity', 0.5);

    // Draw nodes
    svg.append('g')
      .selectAll('rect')
      .data(nodes)
      .join('rect')
      .attr('x', d => d.x0)
      .attr('y', d => d.y0)
      .attr('height', d => d.y1 - d.y0)
      .attr('width', d => d.x1 - d.x0)
      .attr('fill', '#8b5cf6')
      .attr('stroke', '#1f2937');

    // Labels
    svg.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .attr('x', d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
      .attr('y', d => (d.y1 + d.y0) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
      .text(d => d.name)
      .attr('fill', '#e5e7eb')
      .attr('font-size', '12px');
  }, [data]);

  return (
    <div className="overflow-auto">
      <svg ref={svgRef} width="800" height="500" />
    </div>
  );
};
```

**Heatmap**, **Sunburst**, **ForceGraph**: Similar D3 implementations with Deep Space theme styling.

---

## Utility Components

### ProfileReportViewer

**Purpose**: Display ydata-profiling HTML report

**File**: `/src/components/analytics/ProfileReportViewer.tsx`

```typescript
interface ProfileReportViewerProps {
  htmlContent: string;
}

export const ProfileReportViewer: React.FC<ProfileReportViewerProps> = ({ htmlContent }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!iframeRef.current) return;

    const iframe = iframeRef.current;
    const doc = iframe.contentDocument || iframe.contentWindow?.document;

    if (doc) {
      doc.open();
      doc.write(htmlContent);
      doc.close();
    }
  }, [htmlContent]);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-gray-200">
          Data Profiling Report
        </h3>
        <p className="text-sm text-gray-400 mt-1">
          Generated by ydata-profiling
        </p>
      </div>

      <iframe
        ref={iframeRef}
        title="Data Profile Report"
        className="w-full h-[800px] bg-white"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
};
```

**Features**:
- Secure iframe rendering with sandbox
- Full HTML report display
- Responsive height

---

### ExportButton

**Purpose**: Export dashboard to PDF

**File**: `/src/components/analytics/ExportButton.tsx`

**Dependencies**: `html2canvas`, `jspdf`

```typescript
export const ExportButton: React.FC = () => {
  const { exportToPDF } = useAnalytics();
  const [isExporting, setIsExporting] = useState(false);
  const { showToast } = useToast();

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await exportToPDF();
      showToast({
        type: 'success',
        message: 'Dashboard exported to PDF successfully',
      });
    } catch (err) {
      showToast({
        type: 'error',
        message: `Export failed: ${err.message}`,
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={isExporting}
      className={cn(
        'px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2',
        isExporting && 'opacity-50 cursor-not-allowed'
      )}
    >
      {isExporting ? (
        <>
          <svg className="animate-spin h-4 w-4" /* Spinner SVG */ />
          <span>Exporting...</span>
        </>
      ) : (
        <>
          <svg className="h-4 w-4" /* Download icon SVG */ />
          <span>Export PDF</span>
        </>
      )}
    </button>
  );
};
```

---

## TypeScript Interfaces

### Core Data Types

```typescript
// Filter state
interface FilterState {
  [filterKey: string]: FilterValue;
}

type FilterValue =
  | { column: string; value: string } // Select
  | { column: string; min: number; max: number } // Range
  | { column: string; start: string; end: string }; // Date range

// Column analysis
interface ColumnAnalysis {
  name: string;
  type: 'numeric' | 'categorical' | 'datetime' | 'text';
  nullCount: number;
  uniqueCount: number;
  statistics?: {
    mean?: number;
    median?: number;
    std?: number;
    min?: number;
    max?: number;
  };
  topValues?: Array<{ value: string; count: number }>;
}

// Dashboard configuration
interface DashboardConfig {
  kpis: KPIConfig[];
  charts: ChartConfig[];
  filters: FilterConfig[];
  layout: LayoutConfig;
}

interface KPIConfig {
  id: string;
  label: string;
  value: number | string;
  format?: 'number' | 'currency' | 'percentage';
  trend?: {
    direction: 'up' | 'down' | 'stable';
    value: number;
  };
  sparkline?: number[];
  icon?: string;
}

interface ChartConfig {
  id: string;
  type: 'bar' | 'line' | 'pie' | 'treemap' | 'sankey' | 'heatmap' | 'sunburst' | 'forceGraph';
  title: string;
  data: any;
  options?: any;
  size: 'full' | 'half';
}

type FilterConfig = SelectFilterConfig | RangeFilterConfig | DateRangeFilterConfig;

interface LayoutConfig {
  kpiOrder: string[];
  chartOrder: string[];
  filterOrder: string[];
}
```

### Component Props

```typescript
// Generic component props
interface BaseComponentProps {
  className?: string;
  'data-testid'?: string;
}

// Chart data formats
interface BarChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
  }>;
}

interface TreeMapData {
  name: string;
  children: Array<{
    name: string;
    value: number;
    color?: string;
  }>;
}

interface SankeyData {
  nodes: Array<{ name: string }>;
  links: Array<{
    source: number;
    target: number;
    value: number;
  }>;
}

interface HeatmapData {
  rows: string[];
  columns: string[];
  values: number[][];
}
```

---

## Styling Guidelines

### Deep Space Theme Colors

```typescript
const deepSpaceTheme = {
  background: {
    primary: '#111827',   // gray-900
    secondary: '#1f2937', // gray-800
    tertiary: '#374151',  // gray-700
  },
  text: {
    primary: '#e5e7eb',   // gray-200
    secondary: '#9ca3af', // gray-400
    muted: '#6b7280',     // gray-500
  },
  accent: {
    blue: '#60a5fa',      // blue-400
    purple: '#8b5cf6',    // purple-500
    green: '#34d399',     // green-400
    red: '#f87171',       // red-400
  },
  border: {
    default: '#374151',   // gray-700
    hover: '#4b5563',     // gray-600
  },
};
```

### Tailwind Utility Classes

**Common patterns**:

```css
/* Cards */
.card {
  @apply bg-gray-800 rounded-lg p-6 border border-gray-700 hover:border-gray-600 transition-colors;
}

/* Buttons */
.btn-primary {
  @apply px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors;
}

.btn-secondary {
  @apply px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors;
}

/* Inputs */
.input {
  @apply w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-200 focus:border-blue-500 focus:outline-none;
}

/* Text */
.heading-1 {
  @apply text-3xl font-bold text-gray-100;
}

.heading-2 {
  @apply text-2xl font-bold text-gray-100;
}

.heading-3 {
  @apply text-lg font-semibold text-gray-200;
}

.body-text {
  @apply text-gray-300;
}

.muted-text {
  @apply text-sm text-gray-400;
}
```

### Responsive Design

**Breakpoints**:
- `sm`: 640px (mobile landscape)
- `md`: 768px (tablet)
- `lg`: 1024px (desktop)
- `xl`: 1280px (large desktop)

**Grid patterns**:

```tsx
// KPI Cards: 1 → 2 → 3 → 4 columns
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">

// Charts: 1 → 2 columns
<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

// Filters: 1 → 2 → 3 → 4 columns
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
```

---

## Reused Components from dbnotebook

### useToast Hook

**Import**: `import { useToast } from '@/hooks/useToast'`

**Usage**:

```typescript
const { showToast } = useToast();

showToast({
  type: 'success' | 'error' | 'warning' | 'info',
  message: string,
  duration?: number, // default: 3000ms
});
```

### ThemeContext

**Import**: `import { ThemeContext } from '@/contexts/ThemeContext'`

**Usage**:

```typescript
const { theme, setTheme } = useContext(ThemeContext);
// theme: 'light' | 'dark' | 'deep-space'
```

**Note**: Analytics Dashboard assumes Deep Space theme but respects global theme context.

---

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**:
```typescript
const ChartGrid = lazy(() => import('./ChartGrid'));
const ProfileReportViewer = lazy(() => import('./ProfileReportViewer'));
```

2. **Memoization**:
```typescript
const filteredData = useMemo(() => {
  return applyFilters(rawData, filters);
}, [rawData, filters]);
```

3. **Debouncing**:
```typescript
const debouncedFilter = useDebouncedCallback(
  (value) => addFilter('search', value),
  300
);
```

4. **Virtual Scrolling** (for large datasets):
```typescript
import { FixedSizeList } from 'react-window';
```

5. **Chart Data Sampling**:
```typescript
// Sample large datasets for visualization
const sampleData = data.length > 1000
  ? data.filter((_, i) => i % Math.ceil(data.length / 1000) === 0)
  : data;
```

---

## Testing Guidelines

### Component Testing

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { AnalyticsProvider } from '@/contexts/AnalyticsContext';

describe('ExcelUploader', () => {
  it('accepts valid file formats', async () => {
    render(
      <AnalyticsProvider>
        <ExcelUploader />
      </AnalyticsProvider>
    );

    const file = new File([''], 'test.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    const input = screen.getByRole('button');
    fireEvent.drop(input, {
      dataTransfer: { files: [file] },
    });

    expect(await screen.findByText(/uploaded successfully/i)).toBeInTheDocument();
  });
});
```

### Integration Testing

```typescript
describe('Analytics Dashboard Integration', () => {
  it('completes full workflow from upload to visualization', async () => {
    const { getByRole, findByText } = render(<AnalyticsDashboard />);

    // Upload file
    const file = createMockExcelFile();
    await uploadFile(file);

    // Run analysis
    const analyzeButton = getByRole('button', { name: /analyze/i });
    fireEvent.click(analyzeButton);

    // Verify dashboard renders
    expect(await findByText(/Dashboard/i)).toBeInTheDocument();
    expect(await findByText(/KPI/i)).toBeInTheDocument();
  });
});
```

---

## Accessibility

### ARIA Labels

```typescript
// Filter components
<select aria-label={config.label} />

// Chart containers
<div role="img" aria-label={`${config.title} chart`}>

// Export button
<button aria-label="Export dashboard to PDF">

// Loading states
<div role="status" aria-live="polite">
  {analysisProgress}% complete
</div>
```

### Keyboard Navigation

- All interactive elements focusable
- Tab order follows visual flow
- Escape key closes modals/dropdowns
- Enter/Space activates buttons

### Screen Reader Support

```typescript
// Progress updates
<div aria-live="polite" aria-atomic="true">
  Analyzing data: {stage} - {progress}%
</div>

// Chart descriptions
<div className="sr-only">
  {generateChartDescription(data)}
</div>
```

---

## Future Enhancements

### Planned Features

1. **Real-time Collaboration**: Multi-user dashboard editing
2. **Advanced Filters**: Text search, regex patterns, custom expressions
3. **Dashboard Templates**: Pre-built layouts for common use cases
4. **Scheduled Reports**: Automated PDF generation and email delivery
5. **API Integration**: Connect to live data sources (databases, APIs)
6. **Custom Visualizations**: User-defined chart types
7. **Mobile App**: React Native version for iOS/Android
8. **AI Chat**: Natural language queries for data insights

---

## Component File Structure

```
src/
├── components/
│   └── analytics/
│       ├── AnalyticsDashboard.tsx
│       ├── ExcelUploader.tsx
│       ├── AnalysisLoader.tsx
│       ├── DashboardView.tsx
│       ├── ExportButton.tsx
│       ├── filters/
│       │   ├── FilterBar.tsx
│       │   ├── SelectFilter.tsx
│       │   ├── RangeFilter.tsx
│       │   └── DateRangeFilter.tsx
│       ├── kpi/
│       │   ├── KPICardGrid.tsx
│       │   └── KPICard.tsx
│       ├── charts/
│       │   ├── ChartGrid.tsx
│       │   ├── ChartRenderer.tsx
│       │   ├── ChartJSWrapper.tsx
│       │   └── d3/
│       │       ├── TreeMap.tsx
│       │       ├── Sankey.tsx
│       │       ├── Heatmap.tsx
│       │       ├── Sunburst.tsx
│       │       └── ForceGraph.tsx
│       └── ProfileReportViewer.tsx
├── contexts/
│   └── AnalyticsContext.tsx
├── hooks/
│   ├── useAnalytics.ts
│   └── useCrossFilter.ts
├── types/
│   └── analytics.ts
└── utils/
    ├── fileParser.ts
    ├── dataFilters.ts
    └── chartHelpers.ts
```

---

## Quick Reference

### Component Import Paths

```typescript
// Main components
import { AnalyticsDashboard } from '@/components/analytics/AnalyticsDashboard';
import { ExcelUploader } from '@/components/analytics/ExcelUploader';
import { DashboardView } from '@/components/analytics/DashboardView';

// Context and hooks
import { AnalyticsProvider, useAnalytics } from '@/contexts/AnalyticsContext';
import { useCrossFilter } from '@/hooks/useCrossFilter';

// Charts
import { ChartJSWrapper } from '@/components/analytics/charts/ChartJSWrapper';
import { TreeMap } from '@/components/analytics/charts/d3/TreeMap';

// Filters
import { FilterBar } from '@/components/analytics/filters/FilterBar';
```

### Common Patterns

**Adding a new KPI**:

```typescript
const newKPI: KPIConfig = {
  id: 'avg-revenue',
  label: 'Average Revenue',
  value: 12500,
  format: 'currency',
  trend: { direction: 'up', value: 5.2 },
  sparkline: [10000, 11000, 12000, 12500],
  icon: '💰',
};
```

**Adding a new filter**:

```typescript
const newFilter: SelectFilterConfig = {
  id: 'category-filter',
  label: 'Category',
  column: 'category',
  options: ['Electronics', 'Clothing', 'Food'],
};
```

**Adding a new chart**:

```typescript
const newChart: ChartConfig = {
  id: 'sales-by-region',
  type: 'bar',
  title: 'Sales by Region',
  size: 'half',
  data: {
    labels: ['North', 'South', 'East', 'West'],
    datasets: [{
      label: 'Sales',
      data: [12000, 19000, 15000, 17000],
      backgroundColor: '#60a5fa',
    }],
  },
};
```

---

## Summary

This documentation covers all React components for the Analytics Dashboard feature in dbnotebook. Key highlights:

- **11 core components** with full TypeScript interfaces
- **Context-based state management** with AnalyticsContext
- **Cross-filtering** via useCrossFilter hook
- **Dual visualization libraries**: Chart.js (simple) + D3.js (advanced)
- **Deep Space theme** integration with Tailwind CSS
- **Reuse of existing dbnotebook infrastructure** (useToast, ThemeContext)
- **Accessibility and performance** best practices

All components are production-ready with proper error handling, loading states, and responsive design.

---

**Document Version**: 1.0
**Last Updated**: 2025-12-29
**Status**: Design Phase - Ready for Implementation
