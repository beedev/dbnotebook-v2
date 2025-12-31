"""Data profiling using ydata-profiling.

Wraps ydata-profiling to generate statistical insights for dashboard configuration.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

from .types import (
    ProfilingResult,
    ColumnMetadata,
    CorrelationInfo,
    QualityAlert,
    ColumnStatistics,
    CategoricalStats,
)

logger = logging.getLogger(__name__)


class DataProfiler:
    """Generates statistical profiles of datasets using ydata-profiling."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the profiler.

        Args:
            output_dir: Directory for storing HTML reports
        """
        self._output_dir = output_dir or Path("uploads/analytics/profiles")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def profile(
        self,
        df: pd.DataFrame,
        session_id: str,
        title: str = "Analytics Dataset Profile",
        minimal: bool = False,
    ) -> ProfilingResult:
        """Generate a comprehensive profile of the dataset.

        Args:
            df: DataFrame to profile
            session_id: Unique session identifier
            title: Title for the report
            minimal: If True, generate minimal profile (faster)

        Returns:
            ProfilingResult with statistics and HTML report path
        """
        try:
            from ydata_profiling import ProfileReport

            logger.info(f"Generating profile for session {session_id} ({len(df)} rows, {len(df.columns)} cols)")

            # Generate profile report
            profile = ProfileReport(
                df,
                title=title,
                explorative=not minimal,
                minimal=minimal,
                correlations={
                    "auto": {"calculate": True},
                    "pearson": {"calculate": True},
                    "spearman": {"calculate": False},
                },
                missing_diagrams={"heatmap": not minimal, "bar": True},
                samples={"head": 10, "tail": 10},
                progress_bar=False,
            )

            # Save HTML report
            html_path = self._output_dir / f"{session_id}_profile.html"
            profile.to_file(str(html_path))
            logger.info(f"Profile report saved to {html_path}")

            # Extract insights for LLM
            result = self._extract_insights(df, profile, str(html_path))
            return result

        except ImportError:
            logger.warning("ydata-profiling not available, using fallback profiling")
            return self._fallback_profile(df, session_id)

        except Exception as e:
            logger.error(f"Error generating profile: {e}")
            return self._fallback_profile(df, session_id)

    def _extract_insights(
        self,
        df: pd.DataFrame,
        profile: Any,
        html_path: str,
    ) -> ProfilingResult:
        """Extract structured insights from ydata profile.

        Args:
            df: Original DataFrame
            profile: ProfileReport object
            html_path: Path to saved HTML report

        Returns:
            ProfilingResult with extracted insights
        """
        try:
            # Get profile description
            description = profile.get_description()

            # Extract overview
            table_stats = description.get("table", {})
            overview = {
                "row_count": int(table_stats.get("n", len(df))),
                "column_count": int(table_stats.get("n_var", len(df.columns))),
                "missing_cells_percent": float(table_stats.get("p_cells_missing", 0)) * 100,
                "duplicate_rows_percent": float(table_stats.get("p_duplicates", 0)) * 100,
                "memory_size": str(table_stats.get("memory_size", "N/A")),
            }

            # Extract column metadata
            columns = self._extract_column_metadata(df, description)

            # Extract correlations
            correlations = self._extract_correlations(description)

            # Extract quality alerts
            alerts = self._extract_alerts(description)

            # Calculate quality score
            quality_score = self._calculate_quality_score(overview, alerts)

            return ProfilingResult(
                overview=overview,
                columns=columns,
                correlations=correlations,
                quality_alerts=alerts,
                quality_score=quality_score,
                html_report=html_path,
                profile_json=None,  # Can be large, skip for now
            )

        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return self._fallback_profile(df, "unknown")

    def _extract_column_metadata(
        self,
        df: pd.DataFrame,
        description: dict,
    ) -> List[ColumnMetadata]:
        """Extract metadata for each column."""
        columns = []
        variables = description.get("variables", {})

        for col_name in df.columns:
            col_data = df[col_name]
            var_info = variables.get(col_name, {})

            # Infer type
            inferred_type = self._infer_column_type(col_data, var_info)

            # Basic stats
            null_count = int(col_data.isna().sum())
            null_percent = (null_count / len(df)) * 100 if len(df) > 0 else 0
            unique_count = int(col_data.nunique())

            # Sample values (non-null)
            sample_values = col_data.dropna().head(5).tolist()

            # Numeric statistics
            statistics = None
            if inferred_type == "numeric" and pd.api.types.is_numeric_dtype(col_data):
                statistics = self._calculate_numeric_stats(col_data)

            # Categorical statistics
            categorical = None
            if inferred_type == "categorical":
                categorical = self._calculate_categorical_stats(col_data)

            columns.append(ColumnMetadata(
                name=str(col_name),
                inferred_type=inferred_type,
                unique_count=unique_count,
                null_count=null_count,
                null_percent=round(null_percent, 2),
                sample_values=sample_values,
                statistics=statistics,
                categorical=categorical,
            ))

        return columns

    def _infer_column_type(self, col: pd.Series, var_info: dict) -> str:
        """Infer the semantic type of a column."""
        # Check ydata-profiling type first
        ydata_type = var_info.get("type", "")

        if "Numeric" in str(ydata_type):
            return "numeric"
        elif "DateTime" in str(ydata_type):
            return "datetime"
        elif "Boolean" in str(ydata_type):
            return "boolean"
        elif "Categorical" in str(ydata_type):
            return "categorical"

        # Fallback to pandas dtype
        if pd.api.types.is_numeric_dtype(col):
            # Check if it's actually categorical (low cardinality)
            if col.nunique() < 20 and col.nunique() < len(col) * 0.1:
                return "categorical"
            return "numeric"
        elif pd.api.types.is_datetime64_any_dtype(col):
            return "datetime"
        elif pd.api.types.is_bool_dtype(col):
            return "boolean"
        elif col.nunique() < 50:
            return "categorical"
        else:
            return "text"

    def _calculate_numeric_stats(self, col: pd.Series) -> ColumnStatistics:
        """Calculate statistics for numeric column."""
        clean_col = col.dropna()

        if len(clean_col) == 0:
            return ColumnStatistics(
                mean=0, median=0, std=0, min=0, max=0,
                skewness=0, kurtosis=0, quartiles=[0, 0, 0], iqr=0
            )

        q1, q2, q3 = clean_col.quantile([0.25, 0.5, 0.75]).tolist()

        return ColumnStatistics(
            mean=round(float(clean_col.mean()), 4),
            median=round(float(clean_col.median()), 4),
            std=round(float(clean_col.std()), 4),
            min=round(float(clean_col.min()), 4),
            max=round(float(clean_col.max()), 4),
            skewness=round(float(clean_col.skew()), 4) if len(clean_col) > 2 else 0,
            kurtosis=round(float(clean_col.kurtosis()), 4) if len(clean_col) > 3 else 0,
            quartiles=[round(q1, 4), round(q2, 4), round(q3, 4)],
            iqr=round(q3 - q1, 4),
        )

    def _calculate_categorical_stats(self, col: pd.Series) -> CategoricalStats:
        """Calculate statistics for categorical column."""
        value_counts = col.value_counts()
        total = len(col.dropna())

        top_values = []
        for val, count in value_counts.head(10).items():
            top_values.append({
                "value": str(val),
                "count": int(count),
                "percent": round((count / total) * 100, 2) if total > 0 else 0,
            })

        # Calculate entropy
        probs = value_counts / total if total > 0 else value_counts
        entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))

        return CategoricalStats(
            unique_count=int(col.nunique()),
            top_values=top_values,
            entropy=round(entropy, 4),
        )

    def _extract_correlations(self, description: dict) -> List[CorrelationInfo]:
        """Extract high correlations from profile."""
        correlations = []
        corr_data = description.get("correlations", {})

        # Look for Pearson correlations
        pearson = corr_data.get("pearson", {})
        if isinstance(pearson, dict):
            matrix = pearson.get("matrix", {})
            if matrix:
                # Find high correlations (|r| > 0.7)
                processed = set()
                for var1, row in matrix.items():
                    if isinstance(row, dict):
                        for var2, corr_val in row.items():
                            if var1 != var2 and (var2, var1) not in processed:
                                try:
                                    corr = float(corr_val)
                                    if abs(corr) > 0.7:
                                        correlations.append(CorrelationInfo(
                                            var1=str(var1),
                                            var2=str(var2),
                                            correlation=round(corr, 4),
                                        ))
                                        processed.add((var1, var2))
                                except (TypeError, ValueError):
                                    continue

        return correlations

    def _extract_alerts(self, description: dict) -> List[QualityAlert]:
        """Extract quality alerts from profile."""
        alerts = []
        raw_alerts = description.get("alerts", [])

        for alert in raw_alerts:
            if isinstance(alert, dict):
                alerts.append(QualityAlert(
                    column=alert.get("column_name"),
                    severity=self._map_alert_severity(alert.get("alert_type", "")),
                    alert_type=str(alert.get("alert_type", "unknown")),
                    message=str(alert.get("message", "")),
                    recommendation=None,
                ))
            elif hasattr(alert, "column_name"):
                # Handle Alert object
                alerts.append(QualityAlert(
                    column=getattr(alert, "column_name", None),
                    severity=self._map_alert_severity(str(type(alert).__name__)),
                    alert_type=str(type(alert).__name__),
                    message=str(alert),
                    recommendation=None,
                ))

        return alerts

    def _map_alert_severity(self, alert_type: str) -> str:
        """Map alert type to severity level."""
        critical_types = ["High", "Rejected", "Missing", "Constant"]
        warning_types = ["Skewed", "Zeros", "Duplicates", "Correlation"]

        alert_lower = alert_type.lower()
        for t in critical_types:
            if t.lower() in alert_lower:
                return "critical"
        for t in warning_types:
            if t.lower() in alert_lower:
                return "warning"
        return "info"

    def _calculate_quality_score(
        self,
        overview: dict,
        alerts: List[QualityAlert],
    ) -> float:
        """Calculate overall data quality score (0-10)."""
        score = 10.0

        # Penalize for missing data
        missing_percent = overview.get("missing_cells_percent", 0)
        if missing_percent > 50:
            score -= 4
        elif missing_percent > 20:
            score -= 2
        elif missing_percent > 5:
            score -= 1

        # Penalize for duplicates
        dup_percent = overview.get("duplicate_rows_percent", 0)
        if dup_percent > 50:
            score -= 2
        elif dup_percent > 10:
            score -= 1

        # Penalize for alerts
        critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
        warning_count = sum(1 for a in alerts if a.get("severity") == "warning")
        score -= critical_count * 0.5
        score -= warning_count * 0.2

        return max(0, min(10, round(score, 1)))

    def _fallback_profile(self, df: pd.DataFrame, session_id: str) -> ProfilingResult:
        """Generate basic profile without ydata-profiling."""
        logger.info("Using fallback profiling method")

        # Basic overview
        overview = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "missing_cells_percent": (df.isna().sum().sum() / df.size) * 100 if df.size > 0 else 0,
            "duplicate_rows_percent": (df.duplicated().sum() / len(df)) * 100 if len(df) > 0 else 0,
            "memory_size": f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB",
        }

        # Column metadata
        columns = []
        for col_name in df.columns:
            col = df[col_name]
            inferred_type = self._infer_column_type(col, {})

            columns.append(ColumnMetadata(
                name=str(col_name),
                inferred_type=inferred_type,
                unique_count=int(col.nunique()),
                null_count=int(col.isna().sum()),
                null_percent=round((col.isna().sum() / len(df)) * 100, 2) if len(df) > 0 else 0,
                sample_values=col.dropna().head(5).tolist(),
                statistics=self._calculate_numeric_stats(col) if inferred_type == "numeric" else None,
                categorical=self._calculate_categorical_stats(col) if inferred_type == "categorical" else None,
            ))

        return ProfilingResult(
            overview=overview,
            columns=columns,
            correlations=[],
            quality_alerts=[],
            quality_score=7.0,  # Default score for fallback
            html_report=None,
            profile_json=None,
        )
