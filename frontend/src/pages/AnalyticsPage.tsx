/**
 * Analytics Page
 *
 * Standalone page for Excel/CSV analytics.
 * Upload a file and get AI-generated dashboard with KPIs and charts.
 */

import { ArrowLeft } from 'lucide-react';
import { AnalyticsProvider, useAnalytics } from '../contexts/AnalyticsContext';
import { ExcelUploader, DashboardView } from '../components/Analytics';

interface AnalyticsPageProps {
  onBack?: () => void;
  notebookId?: string;
}

function AnalyticsContent({ onBack, notebookId }: AnalyticsPageProps) {
  const { analysisState } = useAnalytics();
  const showDashboard = analysisState === 'complete';

  return (
    <div className="analytics-page">
      <div className="analytics-page__header">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-void-surface text-text-muted hover:text-text hover:bg-void-lighter transition-colors"
          >
            <ArrowLeft size={18} />
            <span>Back to Chat</span>
          </button>
        )}
        <h1 className="analytics-page__title">
          {showDashboard ? '' : 'Data Analytics'}
        </h1>
      </div>

      <div className="analytics-page__content">
        {!showDashboard ? (
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="text-center mb-8 max-w-md">
              <h2 className="text-2xl font-semibold text-text mb-2">
                Analyze Your Data
              </h2>
              <p className="text-text-muted">
                Upload an Excel or CSV file to generate an AI-powered dashboard
                with KPIs, charts, and data quality insights.
              </p>
            </div>
            <ExcelUploader notebookId={notebookId} />
          </div>
        ) : (
          <DashboardView />
        )}
      </div>
    </div>
  );
}

export function AnalyticsPage({ onBack, notebookId }: AnalyticsPageProps) {
  return (
    <AnalyticsProvider>
      <AnalyticsContent onBack={onBack} notebookId={notebookId} />
    </AnalyticsProvider>
  );
}

export default AnalyticsPage;
