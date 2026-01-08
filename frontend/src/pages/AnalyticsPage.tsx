/**
 * Analytics Page
 *
 * Standalone page for Excel/CSV analytics.
 * Upload a file and get AI-generated dashboard with KPIs and charts.
 * Navigation is handled via the global header tabs.
 * Supports auto-analysis when navigating from SQL Chat with results.
 */

import { useEffect, useRef } from 'react';
import { AnalyticsProvider, useAnalytics } from '../contexts/AnalyticsContext';
import { useApp } from '../contexts/AppContext';
import { ExcelUploader, DashboardView } from '../components/Analytics';

interface AnalyticsPageProps {
  notebookId?: string;
}

function AnalyticsContent({ notebookId }: AnalyticsPageProps) {
  const { analysisState, runFullAnalysis, resetDashboard } = useAnalytics();
  const { pendingAnalyticsFile, setPendingAnalyticsFile } = useApp();
  const hasProcessedPendingFile = useRef(false);

  // Auto-run analysis when coming from SQL Chat with a pending file
  useEffect(() => {
    if (pendingAnalyticsFile && !hasProcessedPendingFile.current) {
      hasProcessedPendingFile.current = true;

      // Reset any existing dashboard first
      resetDashboard();

      // Run full analysis on the pending file
      runFullAnalysis(pendingAnalyticsFile, notebookId);

      // Clear the pending file
      setPendingAnalyticsFile(null);
    }
  }, [pendingAnalyticsFile, notebookId, runFullAnalysis, resetDashboard, setPendingAnalyticsFile]);

  // Reset the ref when component unmounts so it can process again next time
  useEffect(() => {
    return () => {
      hasProcessedPendingFile.current = false;
    };
  }, []);

  const showDashboard = analysisState === 'complete';

  return (
    <div className="analytics-page">
      <div className="analytics-page__header">
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

export function AnalyticsPage({ notebookId }: AnalyticsPageProps) {
  return (
    <AnalyticsProvider>
      <AnalyticsContent notebookId={notebookId} />
    </AnalyticsProvider>
  );
}

export default AnalyticsPage;
